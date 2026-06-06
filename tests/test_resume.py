import unittest
from unittest.mock import MagicMock, patch
import os
import json
from core.ocr_parser import DefaultOcrParser
from config.settings import Settings


class TestResume(unittest.TestCase):
    def setUp(self):
        from config import settings as global_settings
        global_settings.BASE_PATH = ""
        global_settings.OUTPUT_CSV = os.path.join(os.getcwd(), "output.csv")
        global_settings.RESUME = False

        self.settings = Settings()
        self.state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
        self.dummy_dir = "/dummy/dir"
        self.state_file_input = os.path.join(self.dummy_dir, ".gaia_resume.json")
        
        # Ensure clean state before each test
        for p in (self.state_file_cwd, self.state_file_input):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
            # Create parent folder for dummy dir if we need a real file system write mock
            # In our tests we will mock path.exists and open or use real files in a temp folder.
            # Let's mock where necessary, or use real files in cwd for simple validation.

    def tearDown(self):
        for p in (self.state_file_cwd, self.state_file_input):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_skips_processed_files(self, mock_exists, mock_listdir):
        # We simulate that file1.pdf is already processed, but file2.pdf is not
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        
        # Mock path.exists to return True for input dir, output csv, and the state files
        mock_exists.side_effect = lambda p: True

        # Write fake resume state to CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.settings.OUTPUT_CSV,
            "processed_files": ["file1.pdf"]
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = self.settings.OUTPUT_CSV

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Execute process with resume=True
        parser.process("/dummy/dir", observer=mock_observer, resume=True)

        # Assert only file2.pdf was processed (so on_file_start called once)
        self.assertEqual(mock_observer.on_file_start.call_count, 1)
        called_args = mock_observer.on_file_start.call_args[0]
        self.assertTrue(called_args[1].endswith("file2.pdf"))

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_auto_resume_without_resume_flag(self, mock_exists, mock_listdir):
        # Even with resume=False, if the file exists in the input dir, it should resume
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": self.settings.OUTPUT_CSV,
            "processed_files": ["file1.pdf"]
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = self.settings.OUTPUT_CSV

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Execute process with resume=False
        parser.process("/dummy/dir", observer=mock_observer, resume=False)

        # Verify it still auto-resumed and processed only file2.pdf
        self.assertEqual(mock_observer.on_file_start.call_count, 1)

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_creates_and_saves_state_both_locations(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["file1.pdf"]
        # Allow exists to return True for dummy_dir so it considers it valid
        mock_exists.side_effect = lambda p: True if p == "/dummy/dir" else False

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = "/dummy/output.csv"

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Verify we write to both CWD and input dir state files
        with patch("config.settings.open", create=True) as mock_open:
            parser.process("/dummy/dir", observer=mock_observer, resume=True)
            # Ensure open was called for both paths
            mock_open.assert_any_call(self.state_file_cwd, "w", encoding="utf-8")
            mock_open.assert_any_call(self.state_file_input, "w", encoding="utf-8")

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_deletes_state_on_success(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": "/dummy/output.csv",
            "processed_files": []
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = "/dummy/output.csv"

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Run process -> complete successfully
        parser.process("/dummy/dir", observer=mock_observer, resume=True)

        # Check that CWD state file was deleted
        self.assertFalse(os.path.isfile(self.state_file_cwd))

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_preserves_state_on_cancel(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": "/dummy/dir",
            "output_file": "/dummy/output.csv",
            "processed_files": ["file1.pdf"]
        }
        with open(self.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = "/dummy/output.csv"

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = True

        parser.process("/dummy/dir", observer=mock_observer, resume=True)

        # Check that state file was NOT deleted (still exists)
        self.assertTrue(os.path.isfile(self.state_file_cwd))


if __name__ == "__main__":
    unittest.main()
