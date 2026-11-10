from unittest import TestCase
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

import main
from app.infrastructure.database.memory import InMemoryClientDatabase
from app.infrastructure.database.registration_repository import InMemoryRegistrationRepository


class RegistrationIntegrationTests(TestCase):
    def test_invitation_registers_client_through_configured_dependency(self):
        # Preserve main's actual router, service and dependency wiring, while
        # keeping the test independent of real Supabase credentials.
        db = InMemoryClientDatabase()
        with (
            patch.object(main.client_service, "db", db),
            patch.object(main.registration_service, "repository", InMemoryRegistrationRepository()),
            patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}),
            TestClient(main.app) as api,
        ):
            response = api.post("/registration-links", headers={"Authorization": "Bearer test-admin"})
            self.assertEqual(response.status_code, 201, response.text)
            link = response.json()
            expected_base = main.registration_service.frontend_url
            self.assertTrue(link["url"].startswith(expected_base + "/cadastro/"))
            token = urlsplit(link["url"]).path.rsplit("/", 1)[1]
            endpoint = f"/registration-links/{token}"
            self.assertEqual(api.get(endpoint).json(), {"valid": True})

            response = api.post(
                endpoint + "/register",
                json={
                    "name": "Maria Silva",
                    "email": "maria@example.com",
                    "phone": "11999999999",
                },
            )
            self.assertEqual(response.status_code, 201, response.text)
            client = response.json()["client"]
            self.assertEqual(db.get_by_id(client["id"]).email, "maria@example.com")
            self.assertEqual(api.get(endpoint).status_code, 410)
            self.assertEqual(len(db.list_all()), 1)

    def test_registration_routes_are_in_openapi(self):
        paths = main.app.openapi()["paths"]
        self.assertIn("post", paths["/registration-links"])
        self.assertIn("get", paths["/registration-links/{token}"])
        self.assertIn("post", paths["/registration-links/{token}/register"])
