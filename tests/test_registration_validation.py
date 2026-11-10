from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from app.api.registration_endpoints import get_registration_service
from app.infrastructure.database.base import ClientDatabaseError
from app.infrastructure.database.memory import InMemoryClientDatabase
from app.infrastructure.database.registration_repository import InMemoryRegistrationRepository
from app.services.client_service import ClientService
from app.services.registration_service import RegistrationService


class RegistrationValidationTests(TestCase):
    def setUp(self):
        self.db = InMemoryClientDatabase()
        self.repository = InMemoryRegistrationRepository()
        self.clients = ClientService(self.db)
        self.service = RegistrationService(self.repository, self.clients, "https://example.com")
        original = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[get_registration_service] = lambda: self.service
        self.addCleanup(self.restore_overrides, original)
        self.api = TestClient(main.app, raise_server_exceptions=False)
        self.addCleanup(self.api.close)
        self.token = self.service.create_link()["url"].rsplit("/", 1)[1]
        self.url = f"/registration-links/{self.token}"
        self.data = {"name": "Maria Silva", "email": "maria@example.com", "phone": "11999999999"}

    def restore_overrides(self, original):
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(original)

    def test_invalid_form_returns_422_without_consuming_invitation(self):
        payloads = [
            {},
            {**self.data, "name": " \t\n "},
            {**self.data, "name": " A "},
            {**self.data, "name": "A" * 151},
            {**self.data, "phone": " \t\n     "},
            {**self.data, "phone": " 1234567 "},
            {**self.data, "phone": "1" * 31},
            {**self.data, "phone": 11999999999},
            {**self.data, "email": "invalid"},
            {**self.data, "name": None},
            {**self.data, "phone": None},
            {**self.data, "email": None},
            {**self.data, "id": "injected-id"},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.api.post(self.url + "/register", json=payload)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(self.api.get(self.url).json(), {"valid": True})
                self.assertEqual(self.db.list_all(), [])
        self.assertEqual(self.api.post(self.url + "/register", json=self.data).status_code, 201)

    def test_form_is_normalized_before_saving(self):
        response = self.api.post(self.url + "/register", json={
            key: f" \t{value}\n " for key, value in self.data.items()
        })
        self.assertEqual(response.status_code, 201, response.text)
        client = response.json()["client"]
        self.assertEqual({key: client[key] for key in self.data}, self.data)
        self.assertEqual(self.db.get_by_id(client["id"]).name, "Maria Silva")

    def test_invitation_errors_return_410_for_validation_and_registration(self):
        link = self.repository.find_by_hash(self.service._hash_token(self.token))
        for state, detail in (("invalid", "Link inválido"), ("expired", "Link expirado"), ("used", "Link já utilizado")):
            link.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            link.used_at = None
            url = self.url
            if state == "invalid":
                url = "/registration-links/unknown"
            elif state == "expired":
                link.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            else:
                link.used_at = datetime.now(timezone.utc)
            with self.subTest(state=state):
                for response in (self.api.get(url), self.api.post(url + "/register", json=self.data)):
                    self.assertEqual(response.status_code, 410)
                    self.assertEqual(response.json(), {"detail": detail})
        self.assertEqual(self.db.list_all(), [])

    def test_internal_value_error_is_not_reported_as_invitation_error(self):
        with patch.object(self.clients, "create_client", side_effect=ValueError("internal details")):
            response = self.api.post(self.url + "/register", json=self.data)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("internal details", response.text)
        self.assertEqual(self.api.get(self.url).json(), {"valid": True})

    def test_database_failure_returns_503_and_preserves_invitation(self):
        with patch.object(self.db, "create", side_effect=ClientDatabaseError("internal details")):
            response = self.api.post(self.url + "/register", json=self.data)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("internal details", response.text)
        self.assertEqual(self.api.get(self.url).json(), {"valid": True})
        self.assertEqual(self.api.post(self.url + "/register", json=self.data).status_code, 201)

    def test_simultaneous_http_registrations_consume_invitation_only_once(self):
        start = Barrier(4)

        def register(_):
            with TestClient(main.app) as api:
                start.wait(timeout=10)
                return api.post(self.url + "/register", json=self.data)

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(register, range(4)))
        self.assertEqual(sorted(response.status_code for response in responses), [201, 410, 410, 410])
        self.assertEqual(len(self.db.list_all()), 1)
        for response in responses:
            if response.status_code == 410:
                self.assertEqual(response.json(), {"detail": "Link já utilizado"})

    def test_failed_invitation_creation_returns_no_url_and_retry_succeeds(self):
        with (
            patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}),
            patch.object(self.repository, "save", side_effect=RuntimeError("internal storage details")),
        ):
            response = self.api.post("/registration-links", headers={"Authorization": "Bearer test-admin"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("internal storage details", response.text)
        self.assertNotIn("https://example.com/cadastro/", response.text)
        with patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}):
            response = self.api.post("/registration-links", headers={"Authorization": "Bearer test-admin"})
        self.assertEqual(response.status_code, 201)
        token = response.json()["url"].rsplit("/", 1)[1]
        self.assertEqual(self.api.get(f"/registration-links/{token}").json(), {"valid": True})
