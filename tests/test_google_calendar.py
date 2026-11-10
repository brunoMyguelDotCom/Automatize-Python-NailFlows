import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch, Mock
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials

from app.api.google_endpoints import router
from app.infrastructure.calendar.google import GoogleCalendar, CalendarError, SCOPES
from app.domain.models import AppointmentCreate
from app.infrastructure.database.memory import InMemoryDatabase
from app.services.appointment_service import AppointmentService


class GoogleCalendarTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = {"GOOGLE_CLIENT_ID": "test", "GOOGLE_CLIENT_SECRET": "secret",
               "GOOGLE_TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
               "GOOGLE_TOKEN_FILE": str(Path(self.temp.name) / "token.enc"),
               "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/google/callback"}
        self.env = patch.dict(os.environ, env)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.google = GoogleCalendar()
        self.creds = Credentials("private-access", refresh_token="private-refresh",
                                 token_uri="https://oauth2.googleapis.com/token",
                                 client_id="test", client_secret="secret", scopes=SCOPES,
                                 expiry=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1))

    def test_encryption_and_refresh(self):
        self.google._save(self.creds)
        self.assertNotIn(b"private-refresh", self.google.token_path.read_bytes())
        self.assertEqual(self.google.token_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.google._credentials().token, "private-access")
        self.creds.expiry = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        self.google._save(self.creds)
        def refresh(creds, request):
            creds.token = "renewed"
            creds.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        with patch.object(Credentials, "refresh", refresh):
            self.assertEqual(self.google._credentials().token, "renewed")
        self.assertEqual(self.google._credentials().token, "renewed")

    def test_callback_state_cookie_and_single_use(self):
        url = self.google.begin("browser")
        state = parse_qs(urlparse(url).query)["state"][0]
        flow = Mock()
        flow.credentials = self.creds
        with patch.object(self.google, "_flow", return_value=flow):
            self.google.finish(state, "code", "browser")
            flow.fetch_token.assert_called_once_with(code="code", timeout=20)
            with self.assertRaises(ValueError):
                self.google.finish(state, "code", "browser")
        state = parse_qs(urlparse(self.google.begin("browser")).query)["state"][0]
        with patch.object(self.google, "_flow") as flow:
            with self.assertRaises(ValueError):
                self.google.finish(state, "code", "attacker")
            flow.assert_not_called()

    def test_routes_require_admin_and_do_not_expose_tokens(self):
        app = FastAPI()
        app.state.google_calendar = self.google
        app.include_router(router)
        with patch.dict("os.environ", {"ADMIN_API_TOKEN": "test-admin"}), TestClient(app) as client:
            self.assertEqual(client.get("/auth/google/connect").status_code, 401)
            response = client.get("/auth/google/connect", headers={"Authorization": "Bearer test-admin"}, follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            self.assertNotIn("www-authenticate", response.headers)
            self.assertIn("AdminToken", app.openapi()["components"]["securitySchemes"])
            self.assertIn("HttpOnly", response.headers["set-cookie"])
            state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
            with patch.object(self.google, "_flow") as flow:
                flow.return_value.credentials = self.creds
                response = client.get("/auth/google/callback", params={"state": state, "code": "test"})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("private-access", response.text)
            self.assertEqual(client.get("/auth/google/callback", params={"state": state, "code": "test"}).status_code, 400)

    def test_crud_and_recover_unsynced_appointment(self):
        data = AppointmentCreate(client={"name": "Teste", "email": "test@example.com"}, service="Gel",
                                 start_time=datetime.now(timezone.utc) + timedelta(days=1), duration_minutes=60)
        db = InMemoryDatabase()
        service = AppointmentService(db, self.google)
        with patch.object(self.google, "_request", side_effect=CalendarError("Falha")):
            with self.assertRaises(CalendarError):
                service.create_appointment(data)
        appointment = db.list_all()[0]
        with patch.object(self.google, "_request", return_value={"id": "event", "attendees": []}) as request:
            recovered = service.synchronize_status(appointment.id)
            self.assertEqual(recovered.sync_state.google_event_id, "event")
            body = request.call_args_list[0].kwargs["json"]
            self.assertEqual(body["start"]["dateTime"], data.start_time.isoformat())
            self.assertEqual(body["attendees"][0]["email"], "test@example.com")
            updated = service.update_appointment(appointment.id, data)
            self.assertEqual(updated.sync_state.google_event_id, "event")
            self.assertTrue(service.cancel_appointment(appointment.id))
            self.assertTrue(any(call.args[0] == "PATCH" for call in request.call_args_list))
            self.assertEqual(request.call_args.args[0], "DELETE")
