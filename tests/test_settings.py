from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.config.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_load_settings_calls_load_dotenv_before_env_reads(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as defaults:
            defaults.write("{}")
            defaults_path = defaults.name

        def _seed_env() -> bool:
            os.environ["OPENAI_API_KEY"] = "dotenv-loaded-key"
            return True

        try:
            with patch.dict(os.environ, {}, clear=True):
                with patch("goldbot.config.settings.load_dotenv", side_effect=_seed_env) as mocked_load_dotenv:
                    settings = load_settings(defaults_path=defaults_path)
                    self.assertEqual(settings.openai_api_key, "dotenv-loaded-key")
                    mocked_load_dotenv.assert_called_once_with()
        finally:
            os.unlink(defaults_path)


if __name__ == "__main__":
    unittest.main()
