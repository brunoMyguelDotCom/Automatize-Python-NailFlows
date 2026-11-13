from contextlib import closing
from unittest import TestCase
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.api.endpoints import get_service_service
from main import app


class AdminSecurityTests(TestCase):
    def test_all_administrative_operations_reject_missing_and_invalid_tokens(self):
        with patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}), closing(TestClient(app)) as api:
            for path, operations in app.openapi()["paths"].items():
                if path == "/servicos/keepalive":
                    continue
                if not path.startswith(("/clientes", "/agendamentos", "/servicos")) and path != "/registration-links":
                    continue
                for method in operations:
                    for authorization in (None, "Bearer wrong", "Basic test-admin"):
                        with self.subTest(path=path, method=method, auth=authorization):
                            headers = {"Authorization": authorization} if authorization else {}
                            response = api.request(method, path.replace("{id}", "test"), headers=headers)
                            self.assertEqual(response.status_code, 401, response.text)
                            self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_unconfigured_admin_fails_closed_but_invitation_validation_is_public(self):
        with patch.dict("os.environ", {"ADMIN_API_TOKEN": ""}), closing(TestClient(app)) as api:
            self.assertEqual(api.post("/registration-links").status_code, 503)
            self.assertEqual(api.get("/clientes/").status_code, 503)
            self.assertEqual(api.get("/registration-links/invalid-token").status_code, 410)
            self.assertEqual(api.post(
                "/registration-links/invalid-token/register",
                json={"name": "Maria", "email": "maria@example.com", "phone": "11999999999"},
            ).status_code, 410)

    def test_valid_admin_can_access_clients(self):
        with patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}), closing(TestClient(app)) as api:
            from unittest.mock import Mock
            import main
            with patch.object(main.client_service, "list_clients", Mock(return_value=[])):
                self.assertEqual(api.get("/clientes/", headers={
                    "Authorization": "Bearer test-admin"
                }).status_code, 200)

    def test_service_keepalive_is_public(self):
        with patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}), closing(TestClient(app)) as api:
            service = Mock()
            service.list_services.return_value = []
            original = app.dependency_overrides.get(get_service_service)
            app.dependency_overrides[get_service_service] = lambda: service
            try:
                response = api.get("/servicos/keepalive")
            finally:
                if original is None:
                    app.dependency_overrides.pop(get_service_service, None)
                else:
                    app.dependency_overrides[get_service_service] = original
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok", "services": 0})
            service.list_services.assert_called_once_with(active_only=False)
