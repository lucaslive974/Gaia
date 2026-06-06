import unittest
from unittest.mock import MagicMock, patch
import os
import json
from core.ocr_parser import DefaultOcrParser
from config.settings import Settings


class TestResume(unittest.TestCase):
    def setUp(self):
        self.state_file = os.path.join(os.getcwd(), ".gaia_resume.json")
        # Ensure clean state before each test
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

    def tearDown(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_skips_processed_files(self, mock_exists, mock_listdir):
        # We simulate that file1.pdf is already processed, but file2.pdf is not
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        
        # Mock path.exists to return True for input dir, output csv, and the state file
        mock_exists.side_effect = lambda p: True

        # Write fake resume state
        state_data = {
            "input_dir": "/dummy/dir",
            "output_csv": "/dummy/output.csv",
            "processed_files": ["file1.pdf"]
        }
        with open(self.state_file, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = "/dummy/output.csv"

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Execute process with resume=True
        parser.process("/dummy/dir", observer=mock_observer, resume=True)

        # Assert only file2.pdf was processed (so on_file_start called once)
        self.assertEqual(mock_observer.on_file_start.call_count, 1)
        # Verify the file passed was file2.pdf
        called_args = mock_observer.on_file_start.call_args[0]
        # called_args: (file_index, file_path, est_hours)
        self.assertTrue(called_args[1].endswith("file2.pdf"))

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_mismatch_does_not_skip(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # State output path is different from current run
        state_data = {
            "input_dir": "/dummy/dir",
            "output_csv": "/different/output.csv",
            "processed_files": ["file1.pdf"]
        }
        with open(self.state_file, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = "/dummy/output.csv"

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Execute process with resume=True
        parser.process("/dummy/dir", observer=mock_observer, resume=True)

        # Since output mismatched, it should process both file1 and file2 (call_count = 2)
        self.assertEqual(mock_observer.on_file_start.call_count, 2)

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_creates_and_saves_state(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.side_effect = lambda p: True if p == "/dummy/dir" else False

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = "/dummy/output.csv"

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Run parser - will save state during execution
        # Wait, but at the end, if completed successfully, it will delete the state file!
        # So to test if state was written, we can verify that the state file gets created,
        # or mock the json.dump / open inside process.
        with patch("core.ocr_parser.open", create=True) as mock_open:
            parser.process("/dummy/dir", observer=mock_observer, resume=True)
            # Ensure open was called with write mode to save state
            mock_open.assert_any_call(self.state_file, "w", encoding="utf-8")

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_deletes_state_on_success(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file
        state_data = {
            "input_dir": "/dummy/dir",
            "output_csv": "/dummy/output.csv",
            "processed_files": []
        }
        with open(self.state_file, "w", encoding="utf-8") as sf:
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

        # Check that state file was deleted
        self.assertFalse(os.path.isfile(self.state_file))

    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_resume_preserves_state_on_cancel(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file
        state_data = {
            "input_dir": "/dummy/dir",
            "output_csv": "/dummy/output.csv",
            "processed_files": ["file1.pdf"]
        }
        with open(self.state_file, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text"])

        mock_writer = MagicMock()
        mock_writer._path = "/dummy/output.csv"

        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        # Simulate cancellation during processing
        mock_observer.is_cancelled = True

        parser.process("/dummy/dir", observer=mock_observer, resume=True)

        # Check that state file was NOT deleted (still exists or was written)
        self.assertTrue(os.path.isfile(self.state_file))


if __name__ == "__main__":
    unittest.main()
