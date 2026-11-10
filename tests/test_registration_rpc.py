import io
import json
import runpy
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient

from app.domain.models import RegistrationLinkError
from app.domain.models import ClientRecord, ClientRegistrationRequest
from app.infrastructure.database.base import RegistrationDatabaseError
from app.infrastructure.database.registration_repository import (
    InMemoryRegistrationRepository, SupabaseRegistrationRepository,
)
from app.services.registration_service import RegistrationService


class RegistrationRpcTests(TestCase):
    def setUp(self):
        self.repository = SupabaseRegistrationRepository("https://example.supabase.co/", "sb_secret_test")
        self.data = ClientRegistrationRequest(name="Maria Silva", email="maria@example.com", phone="11999999999")
        self.client = ClientRecord(**self.data.model_dump())
        mock = patch("app.infrastructure.database.registration_repository.urlopen")
        self.urlopen = mock.start()
        self.addCleanup(mock.stop)

    def respond(self, rows):
        self.urlopen.return_value = io.BytesIO(json.dumps(rows).encode())

    def test_service_registers_with_one_rpc_and_no_separate_client_insert(self):
        self.respond([self.client.model_dump(mode="json")])
        clients = Mock()
        service = RegistrationService(self.repository, clients, "https://example.com")
        result = service.register_client("raw-token", self.data)
        self.assertEqual(result, self.client)
        clients.create_client.assert_not_called()
        self.urlopen.assert_called_once()
        args, kwargs = self.urlopen.call_args
        request = args[0]
        self.assertEqual(request.full_url, "https://example.supabase.co/rest/v1/rpc/register_client_with_invitation")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(request.get_header("Apikey"), "sb_secret_test")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(json.loads(request.data), {
            "p_token_hash": service._hash_token("raw-token"),
            "p_name": "Maria Silva", "p_email": "maria@example.com", "p_phone": "11999999999",
        })

    def test_legacy_key_authenticates_rpc(self):
        self.repository.key = "eyJ.test.jwt"
        self.respond([self.client.model_dump(mode="json")])
        self.repository.register_client("a" * 64, self.data)
        self.assertEqual(self.urlopen.call_args.args[0].get_header("Authorization"), "Bearer eyJ.test.jwt")

    def fail_with(self, body, status=400):
        self.urlopen.side_effect = HTTPError(self.repository.rpc_url, status, "Error", {}, io.BytesIO(body))

    def test_only_recognized_sql_invitation_errors_become_link_errors(self):
        for message in ("Link inválido", "Link expirado", "Link já utilizado"):
            with self.subTest(message=message):
                self.fail_with(json.dumps({"code": "P0001", "message": message}).encode())
                with self.assertRaisesRegex(RegistrationLinkError, message):
                    self.repository.register_client("a" * 64, self.data)

    def test_permission_missing_function_and_unexpected_errors_are_storage_errors(self):
        for body in (
            b'not json', b'[]',
            b'{"code":"PGRST202","message":"function missing"}',
            b'{"code":"42501","message":"permission denied"}',
            b'{"code":"23514","message":"constraint failed"}',
            b'{"code":"P0001","message":"private internal error"}',
            b'{"code":"22023","message":"Link expirado"}',
        ):
            with self.subTest(body=body):
                self.fail_with(body)
                with self.assertRaises(RegistrationDatabaseError):
                    self.repository.register_client("a" * 64, self.data)

    def test_timeout_or_network_failure_does_not_retry_rpc(self):
        for error in (TimeoutError("timeout"), URLError("offline")):
            with self.subTest(error=error):
                self.urlopen.reset_mock()
                self.urlopen.side_effect = error
                with self.assertRaises(RegistrationDatabaseError):
                    self.repository.register_client("a" * 64, self.data)
                self.urlopen.assert_called_once()

    def test_invalid_success_response_is_not_reported_as_registration(self):
        for rows in ([], {}, [{}], [self.client.model_dump(mode="json")] * 2):
            with self.subTest(rows=rows):
                self.respond(rows)
                with self.assertRaises(RegistrationDatabaseError):
                    self.repository.register_client("a" * 64, self.data)


class RegistrationBackendSelectionTests(TestCase):
    def load_application(self, config):
        with (
            patch("app.infrastructure.database.config.load_supabase_config", return_value=config),
            patch.dict("os.environ", {"CALENDAR_BACKEND": "mock", "ADMIN_API_TOKEN": "test-admin"}),
        ):
            return runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))

    def test_no_credentials_selects_memory(self):
        namespace = self.load_application(("", ""))
        self.assertIsInstance(namespace["registration_repository"], InMemoryRegistrationRepository)

    def test_credentials_select_supabase_and_http_registration_uses_rpc(self):
        namespace = self.load_application(("https://example.supabase.co", "sb_secret_test"))
        self.assertIsInstance(namespace["registration_repository"], SupabaseRegistrationRepository)
        self.assertIs(namespace["registration_service"].repository, namespace["registration_repository"])
        data = {"name": "Maria Silva", "email": "maria@example.com", "phone": "11999999999"}
        created = ClientRecord(**data)
        with (
            patch("app.infrastructure.database.registration_repository.urlopen") as request,
            TestClient(namespace["app"]) as api,
        ):
            request.return_value = io.BytesIO(json.dumps([created.model_dump(mode="json")]).encode())
            response = api.post("/registration-links/token/register", json=data)
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["client"]["id"], created.id)
            for code, message, expected in (
                ("P0001", "Link expirado", 410),
                ("P0001", "Link já utilizado", 410),
                ("P0001", "Link inválido", 410),
                ("PGRST202", "private details", 503),
            ):
                request.side_effect = HTTPError("https://example.com", 400, "Error", {}, io.BytesIO(
                    json.dumps({"code": code, "message": message}).encode()
                ))
                response = api.post("/registration-links/token/register", json=data)
                self.assertEqual(response.status_code, expected, response.text)
                self.assertNotIn("private details", response.text)
