import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Set working directory to Gaia root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import main


class TestCli(unittest.TestCase):
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.os.path.exists")
    @patch("main.os.path.isdir")
    @patch("main.DefaultOcrParser")
    @patch("main.Console")
    @patch("main.Progress")
    def test_cli_execution_flow(self, mock_progress, mock_console, mock_parser_class, mock_isdir, mock_exists, mock_parse_args):
        # Setup mocks
        mock_exists.return_value = True
        mock_isdir.return_value = True
        
        mock_args = MagicMock()
        mock_args.input_dir = "/dummy/input"
        mock_args.output = "/dummy/output.csv"
        mock_args.traineddata = "/dummy/traineddata"
        mock_parse_args.return_value = mock_args
        
        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance
        
        # We need mock parser internal variables for the dashboard print
        mock_parser_instance._total_pages = 10
        mock_parser_instance._successful_pages = 8
        mock_parser_instance._native_pages = 5
        mock_parser_instance._ocr_pages = 3
        
        # Mock os.listdir for file count
        with patch("main.os.listdir", return_value=["file1.pdf", "file2.pdf"]):
            # Execute main
            main()
            
        # Assertions
        mock_parse_args.assert_called_once()
        mock_exists.assert_any_call("/dummy/input")
        mock_isdir.assert_any_call("/dummy/input")
        mock_parser_class.assert_called_once()
        mock_parser_instance.process.assert_called_once()


if __name__ == "__main__":
    unittest.main()
