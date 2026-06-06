import unittest
import os
import json
from unittest.mock import patch, MagicMock
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
            self.settings.OUTPUT_CSV,
            os.path.join(os.getcwd(), "output.csv"),
        )
        self.assertFalse(self.settings.RESUME)

    def test_getitem_success(self):
        """Test accessing settings attributes using dictionary syntax."""
        self.assertEqual(self.settings["BASE_PATH"], "")
        self.assertFalse(self.settings["RESUME"])

    def test_getitem_key_error(self):
        """Test that accessing a non-existent key via dictionary syntax raises KeyError."""
        with self.assertRaises(KeyError):
            _ = self.settings["NON_EXISTENT_KEY"]

    def test_setitem(self):
        """Test modifying settings attributes using dictionary syntax."""
        self.settings["BASE_PATH"] = "/custom/path"
        self.settings["RESUME"] = True
        
        # Verify both dictionary-like and attribute-like access reflect the changes
        self.assertEqual(self.settings["BASE_PATH"], "/custom/path")
        self.assertEqual(self.settings.BASE_PATH, "/custom/path")
        self.assertTrue(self.settings["RESUME"])
        self.assertTrue(self.settings.RESUME)

    def test_contains(self):
        """Test the 'in' operator on the settings object."""
        self.assertTrue("BASE_PATH" in self.settings)
        self.assertTrue("OUTPUT_CSV" in self.settings)
        self.assertTrue("RESUME" in self.settings)
        self.assertFalse("NON_EXISTENT_KEY" in self.settings)

    def test_parse_cmd_args_all_fields(self):
        """Test parse_cmd_args with a Namespace containing all mapped attributes."""
        args = Namespace(
            input_dir="/my/input",
            output="/my/output.csv",
            resume=True,
        )
        self.settings.parse_cmd_args(args)
        
        self.assertEqual(self.settings.BASE_PATH, "/my/input")
        self.assertEqual(self.settings.OUTPUT_CSV, "/my/output.csv")
        self.assertTrue(self.settings.RESUME)

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
        self.assertFalse(self.settings.RESUME)
        self.assertEqual(
            self.settings.OUTPUT_CSV,
            os.path.join(os.getcwd(), "output.csv"),
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

    def test_get_state_file_paths(self):
        paths = self.settings.get_state_file_paths("/dummy/input")
        self.assertEqual(len(paths), 2)
        self.assertIn(os.path.join(os.getcwd(), ".gaia_resume.json"), paths)
        self.assertIn(os.path.join("/dummy/input", ".gaia_resume.json"), paths)

    def test_load_save_clear_resume_state(self):
        input_dir = "/dummy/input"
        state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
        state_file_input = os.path.join(input_dir, ".gaia_resume.json")

        with patch("config.settings.open", create=True) as mock_open:
            self.settings.save_resume_state(input_dir, ["file1.pdf"])
            mock_open.assert_any_call(state_file_cwd, "w", encoding="utf-8")
            mock_open.assert_any_call(state_file_input, "w", encoding="utf-8")

        with patch("config.settings.os.path.exists") as mock_exists, \
             patch("config.settings.open", create=True) as mock_open:
            mock_exists.return_value = True
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps({
                "input_dir": input_dir,
                "output_file": self.settings.OUTPUT_CSV,
                "processed_files": ["file1.pdf"]
            })
            mock_open.return_value.__enter__.return_value = mock_file
            
            state = self.settings.load_resume_state(input_dir)
            self.assertIsNotNone(state)
            self.assertEqual(state["processed_files"], ["file1.pdf"])

        with patch("config.settings.os.path.exists") as mock_exists, \
             patch("config.settings.os.remove") as mock_remove:
            mock_exists.return_value = True
            self.settings.clear_resume_state(input_dir)
            mock_remove.assert_any_call(state_file_cwd)
            mock_remove.assert_any_call(state_file_input)

    def test_parse_cmd_args_value_errors(self):
        # Scenario 1: missing input_dir, resume = False -> should raise ValueError
        args = Namespace(input_dir=None, resume=False, output="/my/output.csv")
        with self.assertRaises(ValueError):
            self.settings.parse_cmd_args(args)

        # Scenario 2: missing input_dir, resume = True but no state file -> should raise ValueError
        with patch.object(self.settings, "load_resume_state", return_value=None):
            args = Namespace(input_dir=None, resume=True, output="/my/output.csv")
            with self.assertRaises(ValueError):
                self.settings.parse_cmd_args(args)

    def test_global_settings_instance(self):
        """Test that the global settings instance exported by the package functions properly."""
        self.assertIn("BASE_PATH", global_settings)
        self.assertIn("OUTPUT_CSV", global_settings)
        self.assertIn("RESUME", global_settings)


if __name__ == "__main__":
    unittest.main()


