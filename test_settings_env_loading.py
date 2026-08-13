import importlib
import os
import sys
import unittest
from types import ModuleType


class SettingsEnvLoadingTests(unittest.TestCase):
    def test_broker_settings_are_read_after_dotenv_load(self):
        module_name = "config.settings"
        keys = [
            "DEMO_BROKER",
            "DEMO_BROKER_MODE",
            "ALPACA_BASE_URL",
            "ALPACA_API_KEY",
            "ALPACA_SECRET_KEY",
        ]
        previous_values = {key: os.environ.get(key) for key in keys}
        previous_module = sys.modules.get(module_name)
        previous_dotenv_module = sys.modules.get("dotenv")

        for key in keys:
            os.environ.pop(key, None)

        def _fake_load_dotenv(*_args, **_kwargs):
            os.environ["DEMO_BROKER"] = "alpaca"
            os.environ["DEMO_BROKER_MODE"] = "paper"
            os.environ["ALPACA_BASE_URL"] = "https://paper-api.alpaca.markets"
            os.environ["ALPACA_API_KEY"] = "test-key"
            os.environ["ALPACA_SECRET_KEY"] = "test-secret"
            return True

        try:
            sys.modules.pop(module_name, None)
            fake_dotenv = ModuleType("dotenv")
            fake_dotenv.load_dotenv = _fake_load_dotenv
            sys.modules["dotenv"] = fake_dotenv

            settings = importlib.import_module(module_name)

            self.assertEqual("alpaca", settings.DEMO_BROKER)
            self.assertEqual("paper", settings.DEMO_BROKER_MODE)
            self.assertEqual("https://paper-api.alpaca.markets", settings.ALPACA_BASE_URL)
            self.assertEqual("test-key", settings.ALPACA_API_KEY)
            self.assertEqual("test-secret", settings.ALPACA_SECRET_KEY)
        finally:
            for key, value in previous_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

            if previous_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous_module

            if previous_dotenv_module is None:
                sys.modules.pop("dotenv", None)
            else:
                sys.modules["dotenv"] = previous_dotenv_module


if __name__ == "__main__":
    unittest.main()