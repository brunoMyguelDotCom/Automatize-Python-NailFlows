"""Regressão: representações de escrita devem incluir relações para o Calendar."""
import io
import json
from datetime import UTC, datetime, timedelta
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from app.domain.models import Appointment, AppointmentCreate, Service
from app.infrastructure.calendar.google import CalendarError, GoogleCalendar
from app.infrastructure.database.supabase import SupabaseDatabase
from app.services.appointment_service import AppointmentService


class CalendarRelationsTests(TestCase):
    def setUp(self):
        self.db = SupabaseDatabase("https://example.supabase.co", "test")
        self.service_record = Service(name="Manicure", duration_minutes=60)
        self.data = AppointmentCreate(
            client_id="client-test", service_id=self.service_record.id,
            start_time=datetime.now(UTC) + timedelta(days=1),
        )
        self.row = {
            "id": "12345678-1234-1234-1234-123456789abc",
            "client_id": self.data.client_id, "service_id": self.data.service_id,
            "start_time": self.data.start_time.isoformat(), "duration_minutes": 60,
            "sync_google_event_id": None, "sync_status": "Pending",
            "clients": {"name": "Cliente Teste", "email": "cliente@example.com"},
            "services": self.service_record.model_dump(mode="json"),
        }
        self.calendar = GoogleCalendar.__new__(GoogleCalendar)
        self.calendar._request = Mock(return_value={"id": "event-test", "attendees": []})
        services = Mock()
        services.get_by_id.return_value = self.service_record
        self.service = AppointmentService(self.db, self.calendar, services)
        self.requests = []

    def respond(self, request, timeout):
        self.requests.append(request)
        if request.method == "GET" and "limit" not in parse_qs(urlparse(request.full_url).query):
            rows = []  # Sem sobreposição
        else:
            if request.data:
                self.row.update(json.loads(request.data))
            rows = [self.row]
        return io.BytesIO(json.dumps(rows).encode())

    def test_creation_loads_client_email_and_service_for_google(self):
        with patch("app.infrastructure.database.supabase.urlopen", side_effect=self.respond):
            saved = self.service.create_appointment(self.data)
        body = self.calendar._request.call_args.kwargs["json"]
        self.assertEqual(body["summary"], "Manicure — Cliente Teste")
        self.assertEqual(body["attendees"], [{"email": "cliente@example.com"}])
        self.assertEqual(saved.sync_state.google_event_id, "event-test")
        for request in self.requests:
            if request.method in ("POST", "PATCH"):
                self.assertEqual(parse_qs(urlparse(request.full_url).query)["select"],
                                 ["*,clients(*),services(*)"])
                self.assertNotIn("client", json.loads(request.data))
                self.assertNotIn("service", json.loads(request.data))

    def test_update_resolves_default_duration_and_relations(self):
        self.row["sync_google_event_id"] = "event-test"
        self.service_record.duration_minutes = 90
        self.row["services"] = self.service_record.model_dump(mode="json")
        with patch("app.infrastructure.database.supabase.urlopen", side_effect=self.respond):
            saved = self.service.update_appointment(self.row["id"], self.data)
        self.assertEqual(saved.duration_minutes, 90)
        body = self.calendar._request.call_args.kwargs["json"]
        self.assertEqual(body["summary"], "Manicure — Cliente Teste")
        self.assertEqual(body["attendees"][0]["email"], "cliente@example.com")
        self.assertEqual(datetime.fromisoformat(body["end"]["dateTime"]) -
                         datetime.fromisoformat(body["start"]["dateTime"]), timedelta(minutes=90))

    def test_missing_relation_produces_calendar_error_without_google_call(self):
        appointment = Appointment(
            **{**self.data.model_dump(), "duration_minutes": 60})
        with self.assertRaises(CalendarError):
            self.calendar.create_event(appointment)
        self.calendar._request.assert_not_called()

    def test_synchronize_records_timestamp(self):
        self.row["sync_google_event_id"] = "event-test"
        self.calendar._request.return_value = {"attendees": [{"responseStatus": "accepted"}]}
        with patch("app.infrastructure.database.supabase.urlopen", side_effect=self.respond):
            saved = self.service.synchronize_status(self.row["id"])
        self.assertIsNotNone(saved.sync_state.last_synced)
        self.assertEqual(saved.sync_state.status.value, "Confirmed")
