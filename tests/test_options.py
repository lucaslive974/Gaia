import unittest
import os
import json
from unittest.mock import patch, MagicMock
from argparse import Namespace
from gaia.options import Options
from gaia.options import options as global_options
from gaia.cli.cli_helper import CliHelper
from gaia.extraction_session import ExtractionSession


class TestOptions(unittest.TestCase):
    def setUp(self):
        # Create a fresh Options instance for each test to ensure isolation
        self.options = Options()

    def test_default_values(self):
        """Test that a new Options instance has the expected default values."""
        self.assertEqual(self.options.BASE_PATH, "")
        self.assertEqual(
            self.options.OUTPUT_CSV,
            os.path.join(os.getcwd(), "output.csv"),
        )
        self.assertFalse(self.options.RESUME)
        self.assertIsNone(self.options.REGEX_FILE)
        self.assertIsNone(self.options.TEST_FILE)
        self.assertFalse(self.options.RECURSIVE)
        self.assertEqual(self.options.PAGES_PER_UNIT, 1)
        self.assertEqual(self.options.LANG, "en")

    def test_getitem_success(self):
        """Test accessing options attributes using dictionary syntax."""
        self.assertEqual(self.options["BASE_PATH"], "")
        self.assertFalse(self.options["RESUME"])
        self.assertIsNone(self.options["REGEX_FILE"])
        self.assertFalse(self.options["RECURSIVE"])

    def test_getitem_key_error(self):
        """Test that accessing a non-existent key via dictionary syntax raises KeyError."""
        with self.assertRaises(KeyError):
            _ = self.options["NON_EXISTENT_KEY"]

    def test_setitem(self):
        """Test modifying options attributes using dictionary syntax."""
        self.options["BASE_PATH"] = "/custom/path"
        self.options["RESUME"] = True
        self.options["REGEX_FILE"] = "/my/regex.json"
        self.options["RECURSIVE"] = True

        # Verify both dictionary-like and attribute-like access reflect the changes
        self.assertEqual(self.options["BASE_PATH"], "/custom/path")
        self.assertEqual(self.options.BASE_PATH, "/custom/path")
        self.assertTrue(self.options["RESUME"])
        self.assertTrue(self.options.RESUME)
        self.assertEqual(self.options["REGEX_FILE"], "/my/regex.json")
        self.assertTrue(self.options["RECURSIVE"])
        self.assertTrue(self.options.RECURSIVE)

    def test_contains(self):
        """Test the 'in' operator on the options object."""
        self.assertTrue("BASE_PATH" in self.options)
        self.assertTrue("OUTPUT_CSV" in self.options)
        self.assertTrue("RESUME" in self.options)
        self.assertTrue("REGEX_FILE" in self.options)
        self.assertTrue("RECURSIVE" in self.options)
        self.assertFalse("NON_EXISTENT_KEY" in self.options)

    def test_setattr_validation_ppu(self):
        with self.assertRaises(ValueError):
            self.options.PAGES_PER_UNIT = 0
        with self.assertRaises(ValueError):
            self.options.PAGES_PER_UNIT = -1
        with self.assertRaises(ValueError):
            self.options.PAGES_PER_UNIT = "invalid"

    def test_setattr_validation_lang(self):
        with self.assertRaises(ValueError):
            self.options.LANG = "fr"
        self.options.LANG = "pt"
        self.assertEqual(self.options.LANG, "pt")

    def test_list_attr(self):
        attrs = self.options.list_attr()
        self.assertIn(("input_dir", "BASE_PATH"), attrs)
        self.assertIn(("output", "OUTPUT_CSV"), attrs)
        self.assertIn(("resume", "RESUME"), attrs)
        self.assertIn(("lang", "LANG"), attrs)


class TestCliHelper(unittest.TestCase):
    def test_parse_and_build_options_all_fields(self):
        """Test parse_and_build_options with a Namespace containing all mapped attributes."""
        args = Namespace(
            input_dir="/my/input",
            output="/my/output.csv",
            resume=True,
            regex="/my/regex.json",
            test=None,
            recursive=True,
            pages_per_unit=5,
            lang="pt",
        )
        options = CliHelper.parse_and_build_options(args)

        self.assertEqual(options.BASE_PATH, "/my/input")
        self.assertEqual(options.OUTPUT_CSV, "/my/output.csv")
        self.assertTrue(options.RESUME)
        self.assertEqual(options.REGEX_FILE, "/my/regex.json")
        self.assertTrue(options.RECURSIVE)
        self.assertEqual(options.PAGES_PER_UNIT, 5)
        self.assertEqual(options.LANG, "pt")

    def test_parse_and_build_options_partial_fields(self):
        """Test parse_and_build_options with a Namespace containing only some mapped attributes."""
        args = Namespace(
            input_dir="/my/input_only",
            regex="/my/regex.json",
            # other attributes are missing
        )
        options = CliHelper.parse_and_build_options(args)

        # Check that present fields were updated
        self.assertEqual(options.BASE_PATH, "/my/input_only")
        self.assertEqual(options.REGEX_FILE, "/my/regex.json")
        # Check that missing fields retained their defaults
        self.assertFalse(options.RESUME)
        self.assertFalse(options.RECURSIVE)
        self.assertEqual(
            options.OUTPUT_CSV,
            os.path.join(os.getcwd(), "output.csv"),
        )

    def test_parse_and_build_options_unmapped_fields_ignored(self):
        """Test that parse_and_build_options ignores attributes not in the mapping."""
        args = Namespace(
            input_dir="/my/input",
            regex="/my/regex.json",
            extra_arg="some_value",
        )
        options = CliHelper.parse_and_build_options(args)

        self.assertEqual(options.BASE_PATH, "/my/input")
        self.assertEqual(options.REGEX_FILE, "/my/regex.json")
        # Ensure extra arg is not set on options
        self.assertFalse(hasattr(options, "extra_arg"))
        self.assertFalse("extra_arg" in options)

    def test_parse_and_build_options_value_errors(self):
        # Scenario 1: missing input_dir, resume = False -> should raise ValueError
        args = Namespace(
            input_dir=None, resume=False, output="/my/output.csv", regex="/my/regex.json"
        )
        with self.assertRaises(ValueError):
            CliHelper.parse_and_build_options(args)

        # Scenario 2: missing input_dir, resume = True but no state file -> should raise ValueError
        with patch("gaia.extraction_session.ExtractionSession.load_state", return_value=None):
            args = Namespace(
                input_dir=None, resume=True, output="/my/output.csv", regex="/my/regex.json"
            )
            with self.assertRaises(ValueError):
                CliHelper.parse_and_build_options(args)

        # Scenario 3: input_dir provided, resume = False, but regex is missing -> should raise ValueError
        args = Namespace(
            input_dir="/my/input", resume=False, output="/my/output.csv", regex=None
        )
        with self.assertRaises(ValueError):
            CliHelper.parse_and_build_options(args)

        # Scenario 4: test mode provided -> input_dir is not required, but regex is required
        args = Namespace(
            input_dir=None,
            resume=False,
            output="/my/output.csv",
            regex="/my/regex.json",
            test="/my/test.pdf",
        )
        options = CliHelper.parse_and_build_options(args)
        self.assertEqual(options.TEST_FILE, "/my/test.pdf")
        self.assertEqual(options.REGEX_FILE, "/my/regex.json")

        # Scenario 5: pages_per_unit less than 1 -> should raise ValueError
        args = Namespace(
            input_dir="/my/input",
            resume=False,
            output="/my/output.csv",
            regex="/my/regex.json",
            pages_per_unit=0,
        )
        with self.assertRaises(ValueError):
            CliHelper.parse_and_build_options(args)

        # Scenario 6: pages_per_unit is negative -> should raise ValueError
        args = Namespace(
            input_dir="/my/input",
            resume=False,
            output="/my/output.csv",
            regex="/my/regex.json",
            pages_per_unit=-5,
        )
        with self.assertRaises(ValueError):
            CliHelper.parse_and_build_options(args)

        # Scenario 7: pages_per_unit is not an integer -> should raise ValueError
        args = Namespace(
            input_dir="/my/input",
            resume=False,
            output="/my/output.csv",
            regex="/my/regex.json",
            pages_per_unit="abc",
        )
        with self.assertRaises(ValueError):
            CliHelper.parse_and_build_options(args)

    def test_global_options_instance(self):
        """Test that the global options instance exported by the package functions properly."""
        self.assertIn("BASE_PATH", global_options)
        self.assertIn("OUTPUT_CSV", global_options)
        self.assertIn("RESUME", global_options)


class TestExtractionSessionState(unittest.TestCase):
    def test_load_save_clear_resume_state(self):
        input_dir = "/dummy/input"
        state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
        state_file_input = os.path.join(input_dir, ".gaia_resume.json")

        options = Options()
        options.BASE_PATH = input_dir
        options.REGEX_FILE = "/my/regex.json"

        session = ExtractionSession(None)
        session.input_dir = options.BASE_PATH
        session.output_file = options.OUTPUT_CSV
        session.regex_file = options.REGEX_FILE
        session.processed_files = ["file1.pdf"]
        session.successful_pages = 10
        session.failed_pages = 2
        session.total_pages = 12

        with patch("gaia.extraction_session.open", create=True) as mock_open:
            session.save_state()
            mock_open.assert_any_call(state_file_cwd, "w", encoding="utf-8")
            mock_open.assert_any_call(state_file_input, "w", encoding="utf-8")

        with patch("gaia.extraction_session.os.path.exists") as mock_exists, patch(
            "gaia.extraction_session.open", create=True
        ) as mock_open:
            mock_exists.return_value = True
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(
                {
                    "input_dir": input_dir,
                    "output_file": options.OUTPUT_CSV,
                    "regex_file": "/my/regex.json",
                    "processed_files": ["file1.pdf"],
                    "successful_pages": 10,
                    "failed_pages": 2,
                    "total_pages": 12,
                }
            )
            mock_open.return_value.__enter__.return_value = mock_file

            state = ExtractionSession.load_state(input_dir)
            self.assertIsNotNone(state)
            self.assertEqual(state["processed_files"], ["file1.pdf"])
            self.assertEqual(state["regex_file"], "/my/regex.json")

        with patch("gaia.extraction_session.os.path.exists") as mock_exists, patch(
            "gaia.extraction_session.os.remove"
        ) as mock_remove:
            mock_exists.return_value = True
            session.clear_state()
            mock_remove.assert_any_call(state_file_cwd)
            mock_remove.assert_any_call(state_file_input)


if __name__ == "__main__":
    unittest.main()
