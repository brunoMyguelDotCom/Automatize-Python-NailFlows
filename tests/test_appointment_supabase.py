import io
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from unittest import TestCase
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.endpoints import get_appointment_service
from app.domain.models import Appointment, AppointmentCreate
from app.infrastructure.calendar.google_mock import GoogleMockCalendar
from app.infrastructure.database.base import AppointmentDatabaseError
from app.infrastructure.database.supabase import SupabaseDatabase
from app.services.appointment_service import AppointmentService
from main import app


class AppointmentSupabaseTests(TestCase):
    def setUp(self):
        self.db = SupabaseDatabase('https://example.supabase.co', 'sb_secret_test')
        self.appointment = Appointment(
            client={'name': 'Teste', 'email': 'teste@example.com'},
            service='Manicure',
            start_time=datetime.now(timezone.utc) + timedelta(days=2),
            duration_minutes=60,
        )
        self.row = self.appointment.model_dump(mode='json', exclude={'end_time'})
        self.urlopen = patch('app.infrastructure.database.supabase.urlopen').start()
        self.addCleanup(patch.stopall)

    def respond(self, rows):
        self.urlopen.return_value = io.BytesIO(json.dumps(rows).encode())

    def request(self):
        return self.urlopen.call_args.args[0]

    def test_create_sends_table_columns_and_returns_persisted_record(self):
        self.respond([self.row])
        self.assertEqual(self.db.create(self.appointment), self.appointment)
        request = self.request()
        self.assertEqual(request.full_url, 'https://example.supabase.co/rest/v1/appointments')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(json.loads(request.data), self.row)
        self.assertNotIn('end_time', json.loads(request.data))
        self.assertEqual(request.get_header('Apikey'), 'sb_secret_test')
        self.assertIsNone(request.get_header('Authorization'))

    def test_read_and_list_convert_database_rows(self):
        self.respond([self.row])
        self.assertEqual(self.db.get_by_id(self.appointment.id), self.appointment)
        self.assertEqual(parse_qs(urlparse(self.request().full_url).query)['id'],
                         ['eq.' + self.appointment.id])
        self.respond([self.row])
        self.assertEqual(self.db.list_all(), [self.appointment])
        self.respond([])
        self.assertIsNone(self.db.get_by_id(self.appointment.id))

    def test_update_persists_sync_state_without_computed_column(self):
        self.appointment.sync_state.google_event_id = 'google_test'
        self.row = self.appointment.model_dump(mode='json', exclude={'end_time'})
        self.respond([self.row])
        self.assertEqual(self.db.update(self.appointment.id, self.appointment), self.appointment)
        request = self.request()
        self.assertEqual(request.get_method(), 'PATCH')
        data = json.loads(request.data)
        self.assertNotIn('id', data)
        self.assertNotIn('end_time', data)
        self.assertEqual(data['sync_state']['google_event_id'], 'google_test')
        self.respond([])
        self.assertIsNone(self.db.update(self.appointment.id, self.appointment))

    def test_delete_reports_actual_database_result(self):
        self.respond([self.row])
        self.assertTrue(self.db.delete(self.appointment.id))
        self.assertEqual(self.request().get_method(), 'DELETE')
        self.respond([])
        self.assertFalse(self.db.delete(self.appointment.id))

    def test_empty_or_invalid_insert_response_is_not_success(self):
        for rows in ([], {}, [{'id': 'invalid'}]):
            with self.subTest(rows=rows):
                self.respond(rows)
                with self.assertRaises(AppointmentDatabaseError):
                    self.db.create(self.appointment)

    def test_api_returns_503_on_database_failure(self):
        self.urlopen.side_effect = URLError('offline')
        previous = app.dependency_overrides.copy()
        self.addCleanup(lambda: setattr(app, 'dependency_overrides', previous))
        app.dependency_overrides[get_appointment_service] = lambda: AppointmentService(
            self.db, GoogleMockCalendar()
        )
        with TestClient(app) as client:
            response = client.post('/agendamentos/', json={
                key: value for key, value in self.row.items() if key != 'id'
            })
        self.assertEqual(response.status_code, 503)

    def test_api_creation_inserts_and_then_saves_calendar_reference(self):
        saved = []
        requests = []

        def respond(request, timeout):
            requests.append(request)
            if request.get_method() == 'POST':
                saved.append(json.loads(request.data))
            elif request.get_method() == 'PATCH':
                saved[0].update(json.loads(request.data))
            return io.BytesIO(json.dumps(saved).encode())

        self.urlopen.side_effect = respond
        previous = app.dependency_overrides.copy()
        self.addCleanup(lambda: setattr(app, 'dependency_overrides', previous))
        app.dependency_overrides[get_appointment_service] = lambda: AppointmentService(
            self.db, GoogleMockCalendar()
        )
        with TestClient(app) as client:
            response = client.post('/agendamentos/', json={
                key: value for key, value in self.row.items() if key != 'id'
            })
            self.assertEqual(response.status_code, 201)
            appointment_id = response.json()['id']
            fetched = client.get('/agendamentos/' + appointment_id)
            self.assertEqual(fetched.status_code, 200)
            self.assertEqual(fetched.json(), response.json())
        self.assertEqual([request.get_method() for request in requests],
                         ['GET', 'POST', 'PATCH', 'GET'])
        self.assertTrue(saved[0]['sync_state']['google_event_id'])

    def test_overlap_handles_utc_database_row_and_local_input(self):
        self.respond([self.row])
        service = AppointmentService(self.db, GoogleMockCalendar())
        local = self.appointment.start_time.astimezone(
            ZoneInfo('America/Sao_Paulo')
        ).replace(tzinfo=None)
        data = AppointmentCreate(**{
            **self.row, 'start_time': local,
        })
        with self.assertRaises(HTTPException) as error:
            service.create_appointment(data)
        self.assertEqual(error.exception.status_code, 400)
        self.assertIn('overlaps', error.exception.detail)
