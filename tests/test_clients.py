from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.client_endpoints import get_client_service
from app.api.endpoints import get_appointment_service
from app.infrastructure.calendar.google_mock import GoogleMockCalendar
from app.infrastructure.database.base import ClientDatabaseError
from app.infrastructure.database.memory import InMemoryClientDatabase, InMemoryDatabase
from app.services.appointment_service import AppointmentService
from app.services.client_service import ClientService
from main import app


class ClientEndpointTests(TestCase):
    def setUp(self):
        self.original_overrides = app.dependency_overrides.copy()
        self.db = InMemoryClientDatabase()
        self.service = ClientService(self.db)
        app.dependency_overrides[get_client_service] = lambda: self.service
        app.dependency_overrides[get_appointment_service] = lambda: AppointmentService(
            InMemoryDatabase(), GoogleMockCalendar()
        )
        self.api = TestClient(app)
        self.addCleanup(self.api.close)
        self.addCleanup(self.restore_overrides)
        self.client_data = {
            "name": "Maria Silva",
            "email": "maria@example.com",
            "phone": "+55 11 99999-9999",
        }

    def restore_overrides(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.original_overrides)

    def create_client(self):
        response = self.api.post("/clientes/", json=self.client_data)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_list_get_and_delete_client(self):
        self.assertEqual(self.api.get("/clientes/").json(), [])
        before = datetime.now(timezone.utc)
        created = self.create_client()
        after = datetime.now(timezone.utc)
        self.assertEqual(UUID(created["id"]).version, 4)
        created_at = datetime.fromisoformat(created["created_at"].replace("Z", "+00:00"))
        self.assertLessEqual(before, created_at)
        self.assertLessEqual(created_at, after)
        self.assertEqual({key: created[key] for key in self.client_data}, self.client_data)

        self.assertEqual(self.api.get("/clientes/").json(), [created])
        url = f"/clientes/{created['id']}"
        self.assertEqual(self.api.get(url).json(), created)
        deleted = self.api.delete(url)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json(), {"detail": "Cliente excluída com sucesso"})
        self.assertEqual(self.api.get(url).status_code, 404)
        self.assertEqual(self.api.get("/clientes/").json(), [])

    def test_partial_update_preserves_other_fields_and_registration_metadata(self):
        created = self.create_client()
        url = f"/clientes/{created['id']}"
        response = self.api.patch(url, json={"phone": "11988887777"})
        self.assertEqual(response.status_code, 200, response.text)
        expected = {**created, "phone": "11988887777"}
        self.assertEqual(response.json(), expected)
        self.assertEqual(self.api.get(url).json(), expected)
        self.assertEqual(self.api.patch(url, json={}).json(), expected)

    def test_name_and_email_can_be_updated(self):
        created = self.create_client()
        response = self.api.patch(
            f"/clientes/{created['id']}",
            json={"name": " Maria Souza ", "email": "souza@example.com"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {**created, "name": "Maria Souza", "email": "souza@example.com"})

    def test_create_rejects_missing_or_invalid_fields(self):
        invalid_payloads = [
            {},
            {key: value for key, value in self.client_data.items() if key != "name"},
            {key: value for key, value in self.client_data.items() if key != "email"},
            {key: value for key, value in self.client_data.items() if key != "phone"},
            {**self.client_data, "name": "   "},
            {**self.client_data, "email": "invalid-email"},
            {**self.client_data, "phone": "   "},
            {**self.client_data, "phone": 11999999999},
            {**self.client_data, "id": str(uuid4())},
            {**self.client_data, "created_at": "2020-01-01T00:00:00Z"},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.assertEqual(self.api.post("/clientes/", json=payload).status_code, 422)
        self.assertEqual(self.api.get("/clientes/").json(), [])

    def test_create_trims_contact_fields_and_generates_distinct_ids(self):
        response = self.api.post(
            "/clientes/",
            json={key: f" {value} " for key, value in self.client_data.items()},
        )
        self.assertEqual(response.status_code, 201, response.text)
        first = response.json()
        self.assertEqual({key: first[key] for key in self.client_data}, self.client_data)
        second = self.create_client()
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(self.api.get("/clientes/").json()), 2)

    def test_invalid_patch_does_not_change_the_client(self):
        created = self.create_client()
        url = f"/clientes/{created['id']}"
        for payload in [
            {"name": None}, {"email": None}, {"phone": None},
            {"name": "  "}, {"email": "invalid-email"}, {"phone": ""},
            {"id": str(uuid4())}, {"created_at": "2020-01-01T00:00:00Z"},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(self.api.patch(url, json=payload).status_code, 422)
                self.assertEqual(self.api.get(url).json(), created)

    def test_unknown_client_returns_404(self):
        url = f"/clientes/{uuid4()}"
        self.assertEqual(self.api.get(url).status_code, 404)
        self.assertEqual(self.api.patch(url, json={"name": "Maria"}).status_code, 404)
        self.assertEqual(self.api.delete(url).status_code, 404)

    def test_invalid_id_returns_422(self):
        url = "/clientes/invalid-id"
        self.assertEqual(self.api.get(url).status_code, 422)
        self.assertEqual(self.api.patch(url, json={"name": "Maria"}).status_code, 422)
        self.assertEqual(self.api.delete(url).status_code, 422)

    def test_database_failure_returns_503_without_internal_details(self):
        with patch.object(self.db, "list_all", side_effect=ClientDatabaseError("internal details")):
            response = self.api.get("/clientes/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("internal details", response.text)

    def test_appointment_accepts_existing_client_payload(self):
        # A criação de agendamentos continua aceitando os dados de contato anteriores.
        response = self.api.post("/agendamentos/", json={
            "client": {"name": "Maria Silva", "email": "maria@example.com"},
            "service": "Alongamento em gel",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "duration_minutes": 120,
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["client"], {
            "name": "Maria Silva", "email": "maria@example.com", "phone": None,
        })
        self.assertEqual(self.api.get("/clientes/").json(), [])

    def test_openapi_exposes_all_client_routes_and_models(self):
        schema = self.api.get("/openapi.json").json()
        self.assertEqual(set(schema["paths"]["/clientes/"]), {"get", "post"})
        self.assertEqual(set(schema["paths"]["/clientes/{id}"]), {"get", "patch", "delete"})
        models = schema["components"]["schemas"]
        self.assertEqual(set(models["ClientCreate"]["required"]), {"name", "email", "phone"})
        self.assertNotIn("id", models["ClientCreate"]["properties"])
        self.assertNotIn("created_at", models["ClientUpdate"]["properties"])
        self.assertEqual(set(models["ClientRecord"]["properties"]), {
            "id", "name", "email", "phone", "created_at",
        })
