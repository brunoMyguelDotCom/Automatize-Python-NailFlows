import io
import json
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from app.infrastructure.database.base import RegistrationDatabaseError
from app.infrastructure.database.registration_repository import (
    RegistrationLink,
    SupabaseRegistrationRepository,
)


class SupabaseRegistrationRepositoryTests(TestCase):
    def setUp(self):
        self.repository = SupabaseRegistrationRepository("https://example.supabase.co/", "sb_secret_test")
        self.link = RegistrationLink("a" * 64, datetime.now(timezone.utc) + timedelta(hours=6))
        self.row = {
            "token_hash": self.link.token_hash,
            "expires_at": self.link.expires_at.isoformat(),
            "used_at": None,
        }
        mock = patch("app.infrastructure.database.supabase.urlopen")
        self.urlopen = mock.start()
        self.addCleanup(mock.stop)

    def respond_with(self, value):
        self.urlopen.return_value = io.BytesIO(json.dumps(value).encode())

    def request(self):
        args, kwargs = self.urlopen.call_args
        self.assertEqual(kwargs["timeout"], 10)
        return args[0]

    def test_save_sends_hash_and_dates_to_registration_table(self):
        self.respond_with([self.row])
        self.repository.save(self.link)
        request = self.request()
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, "https://example.supabase.co/rest/v1/registration_links")
        self.assertEqual(json.loads(request.data), self.row)
        self.assertEqual(request.get_header("Apikey"), "sb_secret_test")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.get_header("Prefer"), "return=representation")

    def test_legacy_service_role_key_uses_bearer_header(self):
        self.repository.key = "eyJ.test.jwt"
        self.respond_with([])
        self.repository.find_by_hash(self.link.token_hash)
        self.assertEqual(self.request().get_header("Authorization"), "Bearer eyJ.test.jwt")

    def test_find_returns_domain_record_with_timezone_aware_dates(self):
        self.row["used_at"] = datetime.now(timezone.utc).isoformat()
        self.respond_with([self.row])
        result = self.repository.find_by_hash(self.link.token_hash)
        self.assertIsInstance(result, RegistrationLink)
        self.assertEqual(result.expires_at, self.link.expires_at)
        self.assertEqual(result.used_at, datetime.fromisoformat(self.row["used_at"]))
        request = self.request()
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(parse_qs(urlparse(request.full_url).query), {
            "token_hash": ["eq." + self.link.token_hash],
            "select": ["token_hash,expires_at,used_at"],
            "limit": ["1"],
        })

    def test_missing_invitation_returns_none(self):
        self.respond_with([])
        self.assertIsNone(self.repository.find_by_hash(self.link.token_hash))

    def test_invalid_database_records_are_storage_errors(self):
        for value in (
            {"error": "unexpected"},
            [{"token_hash": "incomplete"}],
            [{**self.row, "expires_at": "invalid"}],
            [{**self.row, "expires_at": "2026-11-09T12:00:00"}],
            [{**self.row, "token_hash": "b" * 64}],
        ):
            with self.subTest(value=value):
                self.respond_with(value)
                with self.assertRaises(RegistrationDatabaseError):
                    self.repository.find_by_hash(self.link.token_hash)

    def test_empty_insert_response_is_not_success(self):
        self.respond_with([])
        with self.assertRaises(RegistrationDatabaseError):
            self.repository.save(self.link)

    def test_http_network_and_timeout_failures_are_storage_errors(self):
        for operation in (lambda: self.repository.save(self.link), lambda: self.repository.find_by_hash(self.link.token_hash)):
            for error in (
                HTTPError(self.repository.url, 403, "Forbidden", {}, io.BytesIO(b"private details")),
                URLError("unavailable"),
                TimeoutError("timed out"),
            ):
                with self.subTest(operation=operation, error=type(error).__name__):
                    self.urlopen.side_effect = error
                    with self.assertRaises(RegistrationDatabaseError):
                        operation()
