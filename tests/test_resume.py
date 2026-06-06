import unittest
from unittest.mock import MagicMock, patch
import os
import json
from core.app_controller import AppController
from config.settings import Settings


class TestResume(unittest.TestCase):
    def setUp(self):
        from config import settings as global_settings

        global_settings.BASE_PATH = ""
        global_settings.OUTPUT_CSV = os.path.join(os.getcwd(), "output.csv")
        global_settings.RESUME = False
        global_settings.REGEX_FILE = "/dummy/regex.json"
        global_settings.RECURSIVE = False

        self.settings = Settings()
        self.settings.REGEX_FILE = "/dummy/regex.json"
        self.settings.BASE_PATH = "/dummy/dir"
        self.state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
        self.dummy_dir = "/dummy/dir"
        self.state_file_input = os.path.join(self.dummy_dir, ".gaia_resume.json")

        # Patch DefaultOcrParser
        self.parser_patcher = patch("core.app_controller.DefaultOcrParser")
        self.mock_parser_class = self.parser_patcher.start()
        self.mock_parser = MagicMock()
        self.mock_parser_class.return_value = self.mock_parser

        # Patch DefaultCsvWriter
        self.csv_patcher = patch("core.app_controller.DefaultCsvWriter")
        self.mock_csv_writer_class = self.csv_patcher.start()
        self.mock_csv_writer = MagicMock()
        self.mock_csv_writer_class.return_value = self.mock_csv_writer

        # Patch NativeRegexEngine
        self.regex_patcher = patch("core.app_controller.NativeRegexEngine")
        self.mock_regex_class = self.regex_patcher.start()
        self.mock_regex = MagicMock()
        self.mock_regex_class.return_value = self.mock_regex

        # Ensure clean state before each test
        for p in (self.state_file_cwd, self.state_file_input):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    def tearDown(self):
        self.parser_patcher.stop()
        self.csv_patcher.stop()
        self.regex_patcher.stop()
        for p in (self.state_file_cwd, self.state_file_input):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    @patch("core.app_controller.os.listdir")
    @patch("core.app_controller.os.path.exists")
    @patch("core.app_controller.os.path.isdir")
    def test_resume_skips_processed_files(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Write fake resume state to CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.settings.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        # Setup mock parser process_file side effect
        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield {"field": "value"}

        self.mock_parser.process_file.side_effect = mock_process_file

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = AppController(observer=mock_observer)
        self.settings.RESUME = True

        success = controller.run(self.settings)
        self.assertTrue(success)

        # Assert only file2.pdf was processed
        self.assertEqual(mock_observer.on_file_start.call_count, 1)
        called_args = mock_observer.on_file_start.call_args[0]
        self.assertTrue(called_args[1].endswith("file2.pdf"))

    @patch("core.app_controller.os.listdir")
    @patch("core.app_controller.os.path.exists")
    @patch("core.app_controller.os.path.isdir")
    def test_auto_resume_without_resume_flag(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.settings.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield {"field": "value"}

        self.mock_parser.process_file.side_effect = mock_process_file

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = AppController(observer=mock_observer)
        self.settings.RESUME = False  # resume flag is false

        success = controller.run(self.settings)
        self.assertTrue(success)

        # Even with resume=False, if the state exists in input dir / cwd, it auto-resumes
        self.assertEqual(mock_observer.on_file_start.call_count, 1)

    @patch("core.app_controller.os.listdir")
    @patch("core.app_controller.os.path.exists")
    @patch("core.app_controller.os.path.isdir")
    def test_resume_creates_and_saves_state_both_locations(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.side_effect = lambda p: True if p == "/dummy/dir" else False

        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield {"field": "value"}

        self.mock_parser.process_file.side_effect = mock_process_file

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = AppController(observer=mock_observer)
        self.settings.RESUME = True

        with patch("config.settings.open", create=True) as mock_open:
            success = controller.run(self.settings)
            self.assertTrue(success)
            mock_open.assert_any_call(self.state_file_cwd, "w", encoding="utf-8")
            mock_open.assert_any_call(self.state_file_input, "w", encoding="utf-8")

    @patch("core.app_controller.os.listdir")
    @patch("core.app_controller.os.path.exists")
    @patch("core.app_controller.os.path.isdir")
    def test_resume_deletes_state_on_success(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.settings.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": [],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield {"field": "value"}

        self.mock_parser.process_file.side_effect = mock_process_file

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = AppController(observer=mock_observer)
        self.settings.RESUME = True

        success = controller.run(self.settings)
        self.assertTrue(success)

        # Check that CWD state file was deleted
        self.assertFalse(os.path.isfile(self.state_file_cwd))

    @patch("core.app_controller.os.listdir")
    @patch("core.app_controller.os.path.exists")
    @patch("core.app_controller.os.path.isdir")
    def test_resume_preserves_state_on_cancel(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.settings.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield {"field": "value"}

        self.mock_parser.process_file.side_effect = mock_process_file

        mock_observer = MagicMock()
        mock_observer.is_cancelled = True  # Cancelled!

        controller = AppController(observer=mock_observer)
        self.settings.RESUME = True

        success = controller.run(self.settings)
        self.assertTrue(success)

        # Check that CWD state file was NOT deleted (still exists)
        self.assertTrue(os.path.isfile(self.state_file_cwd))


if __name__ == "__main__":
    unittest.main()
