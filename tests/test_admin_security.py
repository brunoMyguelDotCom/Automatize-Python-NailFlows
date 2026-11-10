from contextlib import closing
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class AdminSecurityTests(TestCase):
    def test_all_administrative_operations_reject_missing_and_invalid_tokens(self):
        with patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}), closing(TestClient(app)) as api:
            for path, operations in app.openapi()["paths"].items():
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
