import io
import json
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from app.domain.models import ClientRecord
from app.infrastructure.database.base import ClientDatabaseError
from app.infrastructure.database.supabase import SupabaseClientDatabase


class SupabaseClientDatabaseTests(TestCase):
    def setUp(self):
        self.db = SupabaseClientDatabase("https://example.supabase.co/", "sb_secret_test")
        self.client = ClientRecord(name="Maria Silva", email="maria@example.com", phone="11999999999")
        self.urlopen = patch("app.infrastructure.database.supabase.urlopen").start()
        self.addCleanup(patch.stopall)

    def respond_with(self, rows):
        self.urlopen.return_value = io.BytesIO(json.dumps(rows).encode("utf-8"))

    def request(self):
        args, kwargs = self.urlopen.call_args
        self.assertEqual(kwargs["timeout"], 10)
        return args[0]

    def test_create_serializes_all_fields_and_uses_secret_api_key(self):
        data = self.client.model_dump(mode="json")
        self.respond_with([data])
        self.assertEqual(self.db.create(self.client), self.client)
        request = self.request()
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, "https://example.supabase.co/rest/v1/clients")
        self.assertEqual(json.loads(request.data), data)
        self.assertEqual(request.get_header("Apikey"), "sb_secret_test")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.get_header("Prefer"), "return=representation")

    def test_legacy_jwt_key_also_uses_authorization(self):
        self.db.key = "eyJ.test.jwt"
        self.respond_with([])
        self.db.list_all()
        self.assertEqual(self.request().get_header("Authorization"), "Bearer eyJ.test.jwt")

    def test_get_filters_by_id_and_handles_missing_client(self):
        self.respond_with([self.client.model_dump(mode="json")])
        self.assertEqual(self.db.get_by_id(self.client.id), self.client)
        query = parse_qs(urlparse(self.request().full_url).query)
        self.assertEqual(query, {"id": [f"eq.{self.client.id}"], "select": ["*"], "limit": ["1"]})
        self.respond_with([])
        self.assertIsNone(self.db.get_by_id(self.client.id))

    def test_list_returns_records_in_registration_order(self):
        self.respond_with([self.client.model_dump(mode="json")])
        self.assertEqual(self.db.list_all(), [self.client])
        query = parse_qs(urlparse(self.request().full_url).query)
        self.assertEqual(query["order"], ["created_at.asc,id.asc"])

    def test_update_does_not_send_id_or_registration_date(self):
        self.respond_with([self.client.model_dump(mode="json")])
        self.assertEqual(self.db.update(self.client.id, self.client), self.client)
        request = self.request()
        self.assertEqual(request.get_method(), "PATCH")
        self.assertEqual(set(json.loads(request.data)), {"name", "email", "phone"})
        self.assertEqual(parse_qs(urlparse(request.full_url).query), {"id": [f"eq.{self.client.id}"]})
        self.respond_with([])
        self.assertIsNone(self.db.update(self.client.id, self.client))

    def test_delete_reports_whether_a_record_was_removed(self):
        self.respond_with([self.client.model_dump(mode="json")])
        self.assertTrue(self.db.delete(self.client.id))
        self.assertEqual(self.request().get_method(), "DELETE")
        self.assertEqual(parse_qs(urlparse(self.request().full_url).query), {"id": [f"eq.{self.client.id}"]})
        self.respond_with([])
        self.assertFalse(self.db.delete(self.client.id))

    def test_network_errors_are_reported_as_database_failures(self):
        for error in [
            HTTPError(self.db.url, 403, "Forbidden", {}, io.BytesIO(b"private details")),
            URLError("unavailable"),
            TimeoutError("request timed out"),
        ]:
            with self.subTest(error=type(error).__name__):
                self.urlopen.side_effect = error
                with self.assertRaises(ClientDatabaseError):
                    self.db.list_all()

    def test_invalid_response_is_a_database_failure(self):
        for rows in [{"error": "invalid response"}, [{"id": "incomplete"}]]:
            with self.subTest(rows=rows):
                self.respond_with(rows)
                with self.assertRaises(ClientDatabaseError):
                    self.db.list_all()

    def test_empty_create_response_is_not_reported_as_success(self):
        self.respond_with([])
        with self.assertRaises(ClientDatabaseError):
            self.db.create(self.client)
