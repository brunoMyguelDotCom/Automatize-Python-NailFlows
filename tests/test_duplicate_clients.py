import io
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError

from fastapi.testclient import TestClient

import main
from app.api.client_endpoints import get_client_service
from app.api.registration_endpoints import get_registration_service
from app.domain.models import ClientCreate, ClientRegistrationRequest, DuplicateClientError
from app.infrastructure.database.memory import InMemoryClientDatabase
from app.infrastructure.database.registration_repository import InMemoryRegistrationRepository, SupabaseRegistrationRepository
from app.infrastructure.database.supabase import SupabaseClientDatabase
from app.services.client_service import ClientService
from app.services.registration_service import RegistrationService


class DuplicateClientTests(TestCase):
    def setUp(self):
        self.db = InMemoryClientDatabase()
        self.clients = ClientService(self.db)
        self.repository = InMemoryRegistrationRepository()
        self.service = RegistrationService(self.repository, self.clients, "https://example.com")
        original = main.app.dependency_overrides.copy()
        self.addCleanup(self.restore, original)
        main.app.dependency_overrides[get_client_service] = lambda: self.clients
        main.app.dependency_overrides[get_registration_service] = lambda: self.service
        env = patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"})
        env.start()
        self.addCleanup(env.stop)
        self.api = TestClient(main.app)
        self.addCleanup(self.api.close)
        self.auth = {"Authorization": "Bearer test-admin"}
        self.data = {"name": "Maria Silva", "email": "maria@example.com", "phone": "11999999999"}

    def restore(self, original):
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(original)

    def invitation(self):
        return self.service.create_link()["url"].rsplit("/", 1)[1]

    def test_invitation_rejects_email_case_variants_and_phone_formats_without_consuming_link(self):
        self.clients.create_client(ClientCreate(**self.data))
        for field, changes in (
            ("email", {"email": " MARIA@EXAMPLE.COM ", "phone": "21988888888"}),
            ("phone", {"email": "outra@example.com", "phone": "+55 (11) 99999-9999"}),
            ("phone", {"email": "outra@example.com", "phone": "(11) 99999-9999"}),
        ):
            with self.subTest(field=field, changes=changes):
                token = self.invitation()
                endpoint = f"/registration-links/{token}"
                response = self.api.post(endpoint + "/register", json={**self.data, **changes})
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(response.json()["field"], field)
                self.assertEqual(self.api.get(endpoint).json(), {"valid": True})
                self.assertEqual(len(self.db.list_all()), 1)
        response = self.api.post(endpoint + "/register", json={
            **self.data, "email": "nova@example.com", "phone": "31977777777",
        })
        self.assertEqual(response.status_code, 201, response.text)

    def test_administrative_create_and_update_reject_duplicates_and_preserve_data(self):
        first = self.api.post("/clientes/", headers=self.auth, json=self.data).json()
        duplicate = self.api.post("/clientes/", headers=self.auth, json=self.data)
        self.assertEqual(duplicate.status_code, 409)
        second = self.api.post("/clientes/", headers=self.auth, json={
            **self.data, "email": "segunda@example.com", "phone": "21988888888",
        }).json()
        url = f"/clientes/{second['id']}"
        for changes in ({"email": "MARIA@example.com"}, {"phone": "+55 (11) 99999-9999"}):
            response = self.api.patch(url, headers=self.auth, json=changes)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(self.api.get(url, headers=self.auth).json(), second)
        response = self.api.patch(f"/clientes/{first['id']}", headers=self.auth, json={"phone": "+55 (11) 99999-9999"})
        self.assertEqual(response.status_code, 200, response.text)

    def test_distinct_invitations_racing_for_same_contact_create_only_one_client(self):
        tokens = [self.invitation() for _ in range(8)]
        start = Barrier(len(tokens))
        data = ClientRegistrationRequest(**self.data)

        def register(token):
            start.wait(timeout=10)
            try:
                self.service.register_client(token, data)
                return "created"
            except DuplicateClientError:
                return "duplicate"

        with ThreadPoolExecutor(max_workers=len(tokens)) as pool:
            results = list(pool.map(register, tokens))
        self.assertEqual(results.count("created"), 1)
        self.assertEqual(results.count("duplicate"), 7)
        self.assertEqual(len(self.db.list_all()), 1)
        links = [self.repository.find_by_hash(self.service._hash_token(token)) for token in tokens]
        self.assertEqual(sum(link.used_at is not None for link in links), 1)

    def test_supabase_rpc_and_administrative_insert_map_unique_errors_to_409(self):
        for field in ("email", "phone"):
            error_body = json.dumps({
                "code": "23505",
                "message": f'duplicate key value violates unique constraint "clients_{field}_normalized_key"',
                "details": "private client data",
            }).encode()
            for use_rpc in (True, False):
                with self.subTest(field=field, rpc=use_rpc):
                    if use_rpc:
                        repository = SupabaseRegistrationRepository("https://example.supabase.co", "sb_secret_test")
                        self.service.repository = repository
                        target = "app.infrastructure.database.registration_repository.urlopen"
                        url = "/registration-links/token/register"
                    else:
                        self.clients.db = SupabaseClientDatabase("https://example.supabase.co", "sb_secret_test")
                        target = "app.infrastructure.database.supabase.urlopen"
                        url = "/clientes/"
                    with patch(target, side_effect=HTTPError(
                        "https://example.com", 409, "Conflict", {}, io.BytesIO(error_body)
                    )):
                        response = self.api.post(url, headers=self.auth, json=self.data)
                    self.assertEqual(response.status_code, 409, response.text)
                    self.assertEqual(response.json()["field"], field)
                    self.assertNotIn("private client data", response.text)
