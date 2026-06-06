import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Set working directory to Gaia root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import main
from cli.app_controller import AppController
from config.settings import Settings


class TestCli(unittest.TestCase):
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.run_with_ui")
    def test_cli_execution_flow(self, mock_run_with_ui, mock_parse_args):
        # Setup mocks
        mock_args = MagicMock()
        mock_args.input_dir = "/dummy/input"
        mock_args.output = "/dummy/output.csv"
        mock_args.resume = False
        mock_args.regex = "/dummy/regex.json"
        mock_args.test = None
        mock_args.recursive = False
        mock_parse_args.return_value = mock_args

        # Execute main
        main()

        # Assertions
        mock_parse_args.assert_called_once()
        mock_run_with_ui.assert_called_once()
        settings_passed = mock_run_with_ui.call_args[0][0]
        self.assertEqual(settings_passed.BASE_PATH, "/dummy/input")
        self.assertEqual(settings_passed.OUTPUT_CSV, "/dummy/output.csv")
        self.assertFalse(settings_passed.RESUME)
        self.assertEqual(settings_passed.REGEX_FILE, "/dummy/regex.json")

    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.run_with_ui")
    @patch("config.settings.Settings.load_resume_state")
    def test_cli_parameterless_resume_success(
        self, mock_load_resume_state, mock_run_with_ui, mock_parse_args
    ):
        # Setup mock arguments with input_dir = None and resume = True
        mock_args = MagicMock()
        mock_args.input_dir = None
        mock_args.output = "/dummy/output.csv"
        mock_args.resume = True
        mock_args.regex = None
        mock_args.test = None
        mock_args.recursive = False
        mock_parse_args.return_value = mock_args

        # Mock CWD state file loading content
        mock_load_resume_state.return_value = {
            "input_dir": "/loaded/input/dir",
            "output_file": "/loaded/output.csv",
            "regex_file": "/loaded/regex.json",
            "processed_files": ["f1.pdf"],
        }

        # Run main
        main()

        # Assert settings contains the loaded paths from state file
        mock_run_with_ui.assert_called_once()
        settings_passed = mock_run_with_ui.call_args[0][0]
        self.assertEqual(settings_passed.BASE_PATH, "/loaded/input/dir")
        self.assertEqual(settings_passed.OUTPUT_CSV, "/loaded/output.csv")
        self.assertTrue(settings_passed.RESUME)
        self.assertEqual(settings_passed.REGEX_FILE, "/loaded/regex.json")

    @patch("cli.app_controller.os.path.exists")
    @patch("cli.app_controller.os.path.isdir")
    @patch("cli.app_controller.NativeRegexEngine")
    @patch("cli.app_controller.DefaultOcrParser")
    @patch("cli.app_controller.DefaultCsvWriter")
    def test_app_controller_validations_and_run(
        self, mock_csv_writer, mock_parser_class, mock_regex_engine, mock_isdir, mock_exists
    ):
        mock_exists.return_value = True
        mock_isdir.return_value = True

        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance

        mock_observer = MagicMock()
        controller = AppController(observer=mock_observer)

        settings = Settings()
        settings.BASE_PATH = "/dummy/input"
        settings.OUTPUT_CSV = "/dummy/output.csv"
        settings.RESUME = True
        settings.REGEX_FILE = "/dummy/regex.json"

        # mock os.listdir to return empty list so it finishes quickly
        with patch("cli.app_controller.os.listdir", return_value=[]):
            success = controller.run(settings)

        self.assertTrue(success)
        mock_exists.assert_any_call("/dummy/input")
        mock_isdir.assert_any_call("/dummy/input")

    @patch("cli.app_controller.os.path.exists")
    @patch("cli.app_controller.os.path.isdir")
    @patch("cli.app_controller.os.remove")
    @patch("cli.app_controller.NativeRegexEngine")
    @patch("cli.app_controller.DefaultOcrParser")
    def test_app_controller_log_deletion(
        self, mock_parser_class, mock_regex_engine, mock_remove, mock_isdir, mock_exists
    ):
        # Scenario 1: Resume is False -> Should remove gaia_errors.log if it exists
        mock_exists.side_effect = (
            lambda p: True
            if "gaia_errors.log" in p or p == "/dummy/input"
            else False
        )
        mock_isdir.return_value = True

        mock_observer = MagicMock()
        controller = AppController(observer=mock_observer)

        settings = Settings()
        settings.BASE_PATH = "/dummy/input"
        settings.OUTPUT_CSV = "/dummy/output.csv"
        settings.RESUME = False
        settings.REGEX_FILE = "/dummy/regex.json"

        with patch("cli.app_controller.os.listdir", return_value=[]):
            controller.run(settings)
        mock_remove.assert_called_once()

        # Scenario 2: Resume is True -> Should NOT remove gaia_errors.log
        mock_remove.reset_mock()
        settings.RESUME = True
        with patch("cli.app_controller.os.listdir", return_value=[]):
            controller.run(settings)
        mock_remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
