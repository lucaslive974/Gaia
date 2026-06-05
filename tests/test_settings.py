import unittest
import os
from argparse import Namespace
from config.settings import Settings
from config import settings as global_settings


class TestSettings(unittest.TestCase):
    def setUp(self):
        # Create a fresh Settings instance for each test to ensure isolation
        self.settings = Settings()

    def test_default_values(self):
        """Test that a new Settings instance has the expected default values."""
        self.assertEqual(self.settings.BASE_PATH, "")
        self.assertEqual(
            self.settings.TRAINED_DATA_DIR,
            os.path.join(os.getcwd(), "traineddata"),
        )
        self.assertEqual(
            self.settings.OUTPUT_CSV,
            os.path.join(os.getcwd(), "output.csv"),
        )
        self.assertEqual(self.settings.MODE, "native")

    def test_getitem_success(self):
        """Test accessing settings attributes using dictionary syntax."""
        self.assertEqual(self.settings["BASE_PATH"], "")
        self.assertEqual(self.settings["MODE"], "native")

    def test_getitem_key_error(self):
        """Test that accessing a non-existent key via dictionary syntax raises KeyError."""
        with self.assertRaises(KeyError):
            _ = self.settings["NON_EXISTENT_KEY"]

    def test_setitem(self):
        """Test modifying settings attributes using dictionary syntax."""
        self.settings["BASE_PATH"] = "/custom/path"
        self.settings["MODE"] = "ocr"
        
        # Verify both dictionary-like and attribute-like access reflect the changes
        self.assertEqual(self.settings["BASE_PATH"], "/custom/path")
        self.assertEqual(self.settings.BASE_PATH, "/custom/path")
        self.assertEqual(self.settings["MODE"], "ocr")
        self.assertEqual(self.settings.MODE, "ocr")

    def test_contains(self):
        """Test the 'in' operator on the settings object."""
        self.assertTrue("BASE_PATH" in self.settings)
        self.assertTrue("TRAINED_DATA_DIR" in self.settings)
        self.assertTrue("OUTPUT_CSV" in self.settings)
        self.assertTrue("MODE" in self.settings)
        self.assertFalse("NON_EXISTENT_KEY" in self.settings)

    def test_parse_cmd_args_all_fields(self):
        """Test parse_cmd_args with a Namespace containing all mapped attributes."""
        args = Namespace(
            input_dir="/my/input",
            output="/my/output.csv",
            traineddata="/my/traineddata",
            mode="ocr",
        )
        self.settings.parse_cmd_args(args)
        
        self.assertEqual(self.settings.BASE_PATH, "/my/input")
        self.assertEqual(self.settings.OUTPUT_CSV, "/my/output.csv")
        self.assertEqual(self.settings.TRAINED_DATA_DIR, "/my/traineddata")
        self.assertEqual(self.settings.MODE, "ocr")

    def test_parse_cmd_args_partial_fields(self):
        """Test parse_cmd_args with a Namespace containing only some mapped attributes."""
        args = Namespace(
            input_dir="/my/input_only",
            # other attributes are missing
        )
        self.settings.parse_cmd_args(args)
        
        # Check that present fields were updated
        self.assertEqual(self.settings.BASE_PATH, "/my/input_only")
        # Check that missing fields retained their defaults
        self.assertEqual(self.settings.MODE, "native")
        self.assertEqual(
            self.settings.TRAINED_DATA_DIR,
            os.path.join(os.getcwd(), "traineddata"),
        )

    def test_parse_cmd_args_unmapped_fields_ignored(self):
        """Test that parse_cmd_args ignores attributes not in the mapping."""
        args = Namespace(
            input_dir="/my/input",
            extra_arg="some_value",
        )
        self.settings.parse_cmd_args(args)
        
        self.assertEqual(self.settings.BASE_PATH, "/my/input")
        # Ensure extra arg is not set on settings
        self.assertFalse(hasattr(self.settings, "extra_arg"))
        self.assertFalse("extra_arg" in self.settings)

    def test_global_settings_instance(self):
        """Test that the global settings instance exported by the package functions properly."""
        self.assertIn("BASE_PATH", global_settings)
        self.assertIn("TRAINED_DATA_DIR", global_settings)
        self.assertIn("OUTPUT_CSV", global_settings)
        self.assertIn("MODE", global_settings)


if __name__ == "__main__":
    unittest.main()

