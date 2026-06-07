import unittest
from unittest.mock import MagicMock, patch
import os
import json
from gaia.gaia import Gaia
from gaia.config.options import Options


class TestResume(unittest.TestCase):
    def setUp(self):
        from gaia.config import options as global_options

        global_options.BASE_PATH = ""
        global_options.OUTPUT_CSV = os.path.join(os.getcwd(), "output.csv")
        global_options.RESUME = False
        global_options.REGEX_FILE = "/dummy/regex.json"
        global_options.RECURSIVE = False

        self.options = Options()
        self.options.REGEX_FILE = "/dummy/regex.json"
        self.options.BASE_PATH = "/dummy/dir"
        self.state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
        self.dummy_dir = "/dummy/dir"
        self.state_file_input = os.path.join(self.dummy_dir, ".gaia_resume.json")

        # Patch NativePdfParser
        self.parser_patcher = patch("gaia.gaia.NativePdfParser")
        self.mock_parser_class = self.parser_patcher.start()
        self.mock_parser = MagicMock()
        self.mock_parser_class.return_value = self.mock_parser

        # Patch DefaultOutputStream
        self.csv_patcher = patch("gaia.gaia.DefaultOutputStream")
        self.mock_csv_writer_class = self.csv_patcher.start()
        self.mock_csv_writer = MagicMock()
        self.mock_csv_writer_class.return_value = self.mock_csv_writer

        # Patch NativeRegexEngine
        self.regex_patcher = patch("gaia.gaia.NativeRegexEngine")
        self.mock_regex_class = self.regex_patcher.start()
        self.mock_regex = MagicMock()
        self.mock_regex_class.return_value = self.mock_regex
        self.mock_regex_class.from_file.return_value = self.mock_regex

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

    @patch("gaia.gaia.os.listdir")
    @patch("gaia.gaia.os.path.exists")
    @patch("gaia.gaia.os.path.isdir")
    def test_resume_skips_processed_files(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.options.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = Gaia(self.options, observer=mock_observer)
        self.options.RESUME = True

        # Set parse side effect to verify it processes only file2.pdf
        processed_files = []

        def mock_process_file(file_path, session, pages_per_unit=1):
            processed_files.append(os.path.basename(file_path))
            yield (1, 1, "raw text")

        self.mock_parser.process_file.side_effect = mock_process_file
        self.mock_regex.parse.return_value = {"field": "value"}

        success = controller.run(self.options)
        self.assertTrue(success)

        # file1.pdf should be skipped, only file2.pdf processed
        self.assertEqual(processed_files, ["file2.pdf"])

    @patch("gaia.gaia.os.listdir")
    @patch("gaia.gaia.os.path.exists")
    @patch("gaia.gaia.os.path.isdir")
    def test_resume_loads_correct_state_counters(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.options.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            # Check state counters before this page processes
            self.assertEqual(session.successful_pages, 10)
            self.assertEqual(session.failed_pages, 2)
            self.assertEqual(session.total_pages, 12)
            yield (1, 1, "raw text")

        self.mock_parser.process_file.side_effect = mock_process_file
        self.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = Gaia(self.options, observer=mock_observer)
        self.options.RESUME = True

        success = controller.run(self.options)
        self.assertTrue(success)

    @patch("gaia.gaia.os.listdir")
    @patch("gaia.gaia.os.path.exists")
    @patch("gaia.gaia.os.path.isdir")
    def test_resume_saves_updated_state_after_each_file(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.options.OUTPUT_CSV,
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
            yield (1, 1, "raw text")

        self.mock_parser.process_file.side_effect = mock_process_file
        self.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = Gaia(self.options, observer=mock_observer)
        self.options.RESUME = True

        with patch("gaia.extraction_session.open", create=True) as mock_open:
            success = controller.run(self.options)
            self.assertTrue(success)
            mock_open.assert_any_call(self.state_file_cwd, "w", encoding="utf-8")
            mock_open.assert_any_call(self.state_file_input, "w", encoding="utf-8")

    @patch("gaia.gaia.os.listdir")
    @patch("gaia.gaia.os.path.exists")
    @patch("gaia.gaia.os.path.isdir")
    def test_resume_deletes_state_on_success(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.options.OUTPUT_CSV,
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
            yield (1, 1, "raw text")

        self.mock_parser.process_file.side_effect = mock_process_file
        self.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = Gaia(self.options, observer=mock_observer)
        self.options.RESUME = True

        success = controller.run(self.options)
        self.assertTrue(success)

        # Check that CWD state file was deleted
        self.assertFalse(os.path.isfile(self.state_file_cwd))

    @patch("gaia.gaia.os.listdir")
    @patch("gaia.gaia.os.path.exists")
    @patch("gaia.gaia.os.path.isdir")
    def test_resume_preserves_state_on_cancel(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.options.OUTPUT_CSV,
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
            yield (1, 1, "raw text")

        self.mock_parser.process_file.side_effect = mock_process_file
        self.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = True  # Cancelled!

        controller = Gaia(self.options, observer=mock_observer)
        self.options.RESUME = True

        success = controller.run(self.options)
        self.assertTrue(success)

        # Check that CWD state file was NOT deleted (still exists)
        self.assertTrue(os.path.isfile(self.state_file_cwd))

    @patch("gaia.gaia.os.listdir")
    @patch("gaia.gaia.os.path.exists")
    @patch("gaia.gaia.os.path.isdir")
    def test_skip_blank_pages(
        self, mock_isdir, mock_exists, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.return_value = True

        # process_file yields a blank page first, then a non-blank page
        def mock_process_file(file_path, session, pages_per_unit=1):
            yield (1, 2, "   ")        # Blank page!
            yield (2, 2, "raw text")   # Valid page!

        self.mock_parser.process_file.side_effect = mock_process_file
        self.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False
        controller = Gaia(self.options, observer=mock_observer)

        success = controller.run(self.options)
        self.assertTrue(success)

        # The mock_observer should have on_page_start called ONLY for the non-blank page (page 2)
        mock_observer.on_page_start.assert_called_once_with(2, 2)
        # Parse should only have been called with the valid page text
        self.mock_regex.parse.assert_called_once_with("raw text")


if __name__ == "__main__":
    unittest.main()
