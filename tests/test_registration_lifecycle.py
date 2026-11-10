import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from unittest import TestCase
from unittest.mock import patch

from app.domain.models import RegistrationLinkError
from app.domain.models import ClientRegistrationRequest
from app.infrastructure.database.memory import InMemoryClientDatabase
from app.infrastructure.database.registration_repository import InMemoryRegistrationRepository
from app.services.client_service import ClientService
from app.services.registration_service import RegistrationService


class RegistrationLifecycleTests(TestCase):
    def setUp(self):
        self.repository = InMemoryRegistrationRepository()
        self.db = InMemoryClientDatabase()
        self.clients = ClientService(self.db)
        self.service = RegistrationService(self.repository, self.clients, "https://example.com/")
        self.data = ClientRegistrationRequest(
            name="Maria Silva", email="maria@example.com", phone="11999999999"
        )

    def create_token(self):
        return self.service.create_link()["url"].rsplit("/", 1)[1]

    def test_generated_links_are_distinct_and_store_only_hash_with_six_hour_expiry(self):
        now = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
        with patch("app.services.registration_service.datetime") as clock:
            clock.now.return_value = now
            links = [self.service.create_link() for _ in range(20)]
        self.assertEqual(len({link["url"] for link in links}), 20)
        for link in links:
            self.assertTrue(link["url"].startswith("https://example.com/cadastro/"))
            token = link["url"].rsplit("/", 1)[1]
            digest = hashlib.sha256(token.encode()).hexdigest()
            stored = self.repository.find_by_hash(digest)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.expires_at, now + timedelta(hours=6))
            self.assertEqual(datetime.fromisoformat(link["expires_at"]), stored.expires_at)
            self.assertIsNone(stored.used_at)
            self.assertIsNone(self.repository.find_by_hash(token))
            self.assertNotIn(token, vars(stored).values())

    def test_expiration_boundary_without_waiting(self):
        token = self.create_token()
        link = self.repository.find_by_hash(self.service._hash_token(token))
        for offset in (-1, 0, 1):
            now = link.expires_at + timedelta(microseconds=offset)
            with (
                self.subTest(offset=offset),
                patch("app.services.registration_service.datetime") as clock,
                patch("app.infrastructure.database.registration_repository.datetime") as repository_clock,
            ):
                clock.now.return_value = now
                repository_clock.now.return_value = now
                if offset < 0:
                    self.assertEqual(self.service.validate_link(token), {"valid": True})
                else:
                    with self.assertRaisesRegex(RegistrationLinkError, "Link expirado"):
                        self.service.validate_link(token)
                    with self.assertRaisesRegex(RegistrationLinkError, "Link expirado"):
                        self.service.register_client(token, self.data)
        self.assertEqual(self.db.list_all(), [])
        self.assertIsNone(link.used_at)

    def test_reusing_invitation_cannot_create_second_client(self):
        token = self.create_token()
        created = self.service.register_client(token, self.data)
        with self.assertRaisesRegex(RegistrationLinkError, "Link já utilizado"):
            self.service.register_client(token, self.data)
        self.assertEqual(self.db.list_all(), [created])

    def test_concurrent_services_sharing_repository_create_exactly_one_client(self):
        token = self.create_token()
        workers = 8
        start = Barrier(workers)

        def register():
            # Separate services simulate requests sharing one in-process repository.
            service = RegistrationService(self.repository, self.clients, "https://example.com")
            start.wait(timeout=10)
            try:
                return service.register_client(token, self.data)
            except RegistrationLinkError as exc:
                return str(exc)

        with patch.object(self.clients, "create_client", wraps=self.clients.create_client) as create:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(lambda _: register(), range(workers)))
            self.assertEqual(create.call_count, 1)
        self.assertEqual(results.count("Link já utilizado"), workers - 1)
        self.assertEqual(len(self.db.list_all()), 1)
        self.assertEqual(sum(not isinstance(result, str) for result in results), 1)

    def test_failed_link_save_returns_no_invitation_and_can_be_retried(self):
        with patch.object(self.repository, "save", side_effect=RuntimeError("storage unavailable")):
            with self.assertRaisesRegex(RuntimeError, "storage unavailable"):
                self.service.create_link()
        self.assertEqual(self.db.list_all(), [])
        self.assertEqual(self.service.validate_link(self.create_token()), {"valid": True})

    def test_memory_repository_loses_invitation_after_process_restart(self):
        # Documents the current limitation, NOT a persistence acceptance test.
        code = """
import json
from app.infrastructure.database.registration_repository import InMemoryRegistrationRepository
from app.services.registration_service import RegistrationService
service = RegistrationService(InMemoryRegistrationRepository(), None, 'https://example.com')
print(json.dumps(service.create_link()))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=True, timeout=10,
        )
        token = json.loads(result.stdout)["url"].rsplit("/", 1)[1]
        with self.assertRaisesRegex(RegistrationLinkError, "Link inválido"):
            self.service.validate_link(token)
