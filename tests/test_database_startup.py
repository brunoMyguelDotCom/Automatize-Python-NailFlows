from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class DatabaseStartupTests(TestCase):
    def test_startup_with_only_supabase_api_credentials(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_KEY": "test-key",
                },
                clear=True,
            ),
            patch("main.supabase_url", "https://example.supabase.co"),
            patch("main.supabase_key", "test-key"),
            patch("urllib.request.urlopen") as request,
        ):
            with TestClient(app) as client:
                self.assertEqual(client.get("/").status_code, 200)
            request.assert_not_called()
