import os
from unittest import TestCase
from unittest.mock import patch

from app.infrastructure.database.config import load_supabase_config


class DatabaseConfigTests(TestCase):
    def config(self, env):
        with patch.dict(os.environ, env, clear=True), patch(
            "app.infrastructure.database.config.load_dotenv"
        ):
            return load_supabase_config()

    def test_secret_key_from_current_env_format(self):
        self.assertEqual(
            self.config({"SUPABASE_URL": " https://example.supabase.co/ ",
                         "SUPABASE_SECRET_KEY": " sb_secret_test ",
                         "SUPABASE_KEY": "legacy"}),
            ("https://example.supabase.co", "sb_secret_test"),
        )

    def test_legacy_key_is_supported(self):
        self.assertEqual(
            self.config({"SUPABASE_URL": "https://example.supabase.co",
                         "SUPABASE_KEY": "legacy"}),
            ("https://example.supabase.co", "legacy"),
        )

    def test_rest_url_is_normalized_to_project_url(self):
        self.assertEqual(
            self.config({"SUPABASE_URL": "https://example.supabase.co/rest/v1/",
                         "SUPABASE_SECRET_KEY": "sb_secret_test"}),
            ("https://example.supabase.co", "sb_secret_test"),
        )

    def test_no_configuration_uses_memory(self):
        self.assertEqual(self.config({}), ("", ""))

    def test_partial_configuration_does_not_silently_use_memory(self):
        for env in ({"SUPABASE_URL": "https://example.supabase.co"},
                    {"SUPABASE_SECRET_KEY": "sb_secret_test"}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                self.config(env)
