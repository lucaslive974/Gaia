import unittest
import os
from config import settings

class TestSettings(unittest.TestCase):
    def test_settings_keys(self):
        self.assertIn("BASE_PATH", settings)
        self.assertIn("TRAINED_DATA_DIR", settings)
        self.assertIn("OUTPUT_CSV", settings)

    def test_settings_modification(self):
        old_val = settings["BASE_PATH"]
        settings["BASE_PATH"] = "/tmp/test_path"
        self.assertEqual(settings["BASE_PATH"], "/tmp/test_path")
        settings["BASE_PATH"] = old_val  # Restore


if __name__ == "__main__":
    unittest.main()
