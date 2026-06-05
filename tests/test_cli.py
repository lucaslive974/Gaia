import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Set working directory to Gaia root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import main


class TestCli(unittest.TestCase):
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("core.shell_manager.os.path.exists")
    @patch("core.shell_manager.os.path.isdir")
    @patch("core.shell_manager.DefaultOcrParser")
    @patch("core.shell_manager.Console")
    @patch("core.shell_manager.Progress")
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
        with patch("core.shell_manager.os.listdir", return_value=["file1.pdf", "file2.pdf"]):
            # Execute main
            main()
            
        # Assertions
        mock_parse_args.assert_called_once()
        mock_exists.assert_any_call("/dummy/input")
        mock_isdir.assert_any_call("/dummy/input")
        mock_parser_class.assert_called_once()
        mock_parser_instance.process.assert_called_once()

    @patch("core.shell_manager.os.path.exists")
    @patch("core.shell_manager.os.path.isdir")
    @patch("core.shell_manager.DefaultOcrParser")
    @patch("core.shell_manager.Console")
    @patch("core.shell_manager.Progress")
    @patch("core.shell_manager.DefaultCsvWriter")
    @patch("core.shell_manager.OcrPdfExtractor")
    @patch("core.shell_manager.NativePdfExtractor")
    def test_shell_manager_passes_settings_to_components(
        self,
        mock_native_extractor_class,
        mock_ocr_extractor_class,
        mock_csv_writer_class,
        mock_progress,
        mock_console,
        mock_parser_class,
        mock_isdir,
        mock_exists,
    ):
        from core.shell_manager import ShellManager
        from config.settings import Settings

        mock_exists.return_value = True
        mock_isdir.return_value = True

        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance
        mock_parser_instance._total_pages = 0
        mock_parser_instance._successful_pages = 0
        mock_parser_instance._native_pages = 0
        mock_parser_instance._ocr_pages = 0

        # Test scenario 1: OCR Mode
        ocr_settings = Settings()
        ocr_settings.BASE_PATH = "/dummy/input"
        ocr_settings.OUTPUT_CSV = "/dummy/output_ocr.csv"
        ocr_settings.TRAINED_DATA_DIR = "/dummy/traineddata_ocr"
        ocr_settings.MODE = "ocr"

        shell = ShellManager(console=mock_console)
        # Mock listdir to avoid file counting issues
        with patch("core.shell_manager.os.listdir", return_value=[]):
            shell.run(ocr_settings)

        # Assert DefaultCsvWriter was initialized with the custom output path
        mock_csv_writer_class.assert_any_call(path_output="/dummy/output_ocr.csv")
        # Assert OcrPdfExtractor was initialized with the custom traineddata
        mock_ocr_extractor_class.assert_any_call(tessdata_dir="/dummy/traineddata_ocr")

        # Test scenario 2: Native Mode
        mock_csv_writer_class.reset_mock()
        native_settings = Settings()
        native_settings.BASE_PATH = "/dummy/input"
        native_settings.OUTPUT_CSV = "/dummy/output_native.csv"
        native_settings.MODE = "native"

        with patch("core.shell_manager.os.listdir", return_value=[]):
            shell.run(native_settings)

        # Assert DefaultCsvWriter was initialized with the native output path
        mock_csv_writer_class.assert_any_call(path_output="/dummy/output_native.csv")
        # Assert NativePdfExtractor was initialized (takes no args)
        mock_native_extractor_class.assert_any_call()


if __name__ == "__main__":
    unittest.main()

