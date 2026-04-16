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
        fd, defaults_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)

        def _seed_env() -> bool:
            os.environ["OPENAI_API_KEY"] = "dotenv-loaded-key"
            return True

        try:
            with open(defaults_path, "w", encoding="utf-8") as defaults:
                defaults.write("{}")
            with patch.dict(os.environ, {}, clear=True):
                with patch("goldbot.config.settings.load_dotenv", side_effect=_seed_env) as mocked_load_dotenv:
                    settings = load_settings(defaults_path=defaults_path)
                    self.assertEqual(settings.openai_api_key, "dotenv-loaded-key")
                    mocked_load_dotenv.assert_called_once_with()
        finally:
            os.unlink(defaults_path)

    def test_defaults_yaml_ai_timeout_is_60_seconds(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.ai.timeout_seconds, 60)

    def test_defaults_yaml_ai_analysis_bars_is_200(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.ai.analysis_bars, 200)


if __name__ == "__main__":
    unittest.main()
