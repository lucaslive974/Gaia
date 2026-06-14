import os
import json
import pytest
from unittest.mock import MagicMock, patch
from pyingestion.pyingestion import PyIngestion
from pyingestion.options import Options


class TestResumeSession:
    @pytest.fixture
    def resume_setup(self, tmp_path):
        from pyingestion.options import options as global_options

        global_options.BASE_PATH = ""
        global_options.OUTPUT_CSV = os.path.join(tmp_path, "output.csv")
        global_options.RESUME = False
        global_options.REGEX_FILE = "/dummy/regex.json"
        global_options.RECURSIVE = False

        options = Options()
        options.REGEX_FILE = "/dummy/regex.json"
        options.BASE_PATH = os.path.join(tmp_path, "dummy_dir")
        os.makedirs(options.BASE_PATH, exist_ok=True)

        # Mock getcwd to return our tmp_path directory to avoid creating files in actual workspace CWD
        cwd_patcher = patch("os.getcwd", return_value=str(tmp_path))
        cwd_patcher.start()

        state_file_cwd = os.path.join(str(tmp_path), ".gaia_resume.json")
        state_file_input = os.path.join(options.BASE_PATH, ".gaia_resume.json")

        # Patch PdfParser
        parser_patcher = patch("pyingestion.parsers.PdfParser")
        mock_parser_class = parser_patcher.start()
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser

        # Patch DefaultOutputStream
        csv_patcher = patch("pyingestion.pyingestion.DefaultOutputStream")
        mock_csv_writer_class = csv_patcher.start()
        mock_csv_writer = MagicMock()
        mock_csv_writer_class.return_value = mock_csv_writer

        # Patch NativeRegexEngine
        regex_patcher = patch("pyingestion.pyingestion.NativeRegexEngine")
        mock_regex_class = regex_patcher.start()
        mock_regex = MagicMock()
        mock_regex_class.return_value = mock_regex
        mock_regex_class.from_file.return_value = mock_regex

        class Context:
            pass

        ctx = Context()
        ctx.options = options
        ctx.state_file_cwd = state_file_cwd
        ctx.state_file_input = state_file_input
        ctx.mock_parser = mock_parser
        ctx.mock_regex = mock_regex

        yield ctx

        # Teardown
        cwd_patcher.stop()
        parser_patcher.stop()
        csv_patcher.stop()
        regex_patcher.stop()

    @patch("pyingestion.pyingestion.os.listdir")
    @patch("pyingestion.pyingestion.os.path.exists")
    @patch("pyingestion.pyingestion.os.path.isdir")
    def test_resume_skips_processed_files(
        self, mock_isdir, mock_exists, mock_listdir, resume_setup
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD (mocked CWD is tmp_path)
        state_data = {
            "input_dir": resume_setup.options.BASE_PATH,
            "output_file": resume_setup.options.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(resume_setup.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = PyIngestion(resume_setup.options, observer=mock_observer)
        resume_setup.options.RESUME = True

        processed_files = []

        def mock_process_file(file_path, session, pages_per_unit=1):
            processed_files.append(os.path.basename(file_path))
            yield (1, 1, "raw text")

        resume_setup.mock_parser.process_file.side_effect = mock_process_file
        resume_setup.mock_regex.parse.return_value = {"field": "value"}

        success = controller.run(resume_setup.options)
        assert success is True

        # file1.pdf should be skipped, only file2.pdf processed
        assert processed_files == ["file2.pdf"]

    @patch("pyingestion.pyingestion.os.listdir")
    @patch("pyingestion.pyingestion.os.path.exists")
    @patch("pyingestion.pyingestion.os.path.isdir")
    def test_resume_loads_correct_state_counters(
        self, mock_isdir, mock_exists, mock_listdir, resume_setup
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": resume_setup.options.BASE_PATH,
            "output_file": resume_setup.options.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(resume_setup.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            # Check state counters before this page processes
            assert session.successful_pages == 10
            assert session.failed_pages == 2
            assert session.total_pages == 12
            yield (1, 1, "raw text")

        resume_setup.mock_parser.process_file.side_effect = mock_process_file
        resume_setup.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = PyIngestion(resume_setup.options, observer=mock_observer)
        resume_setup.options.RESUME = True

        success = controller.run(resume_setup.options)
        assert success is True

    @patch("pyingestion.pyingestion.os.listdir")
    @patch("pyingestion.pyingestion.os.path.exists")
    @patch("pyingestion.pyingestion.os.path.isdir")
    def test_resume_saves_updated_state_after_each_file(
        self, mock_isdir, mock_exists, mock_listdir, resume_setup
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": resume_setup.options.BASE_PATH,
            "output_file": resume_setup.options.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(resume_setup.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield (1, 1, "raw text")

        resume_setup.mock_parser.process_file.side_effect = mock_process_file
        resume_setup.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = PyIngestion(resume_setup.options, observer=mock_observer)
        resume_setup.options.RESUME = True

        with patch("pyingestion.extraction_session.open", create=True) as mock_open:
            success = controller.run(resume_setup.options)
            assert success is True
            mock_open.assert_any_call(
                resume_setup.state_file_cwd, "w", encoding="utf-8"
            )
            mock_open.assert_any_call(
                resume_setup.state_file_input, "w", encoding="utf-8"
            )

    @patch("pyingestion.pyingestion.os.listdir")
    @patch("pyingestion.pyingestion.os.path.exists")
    @patch("pyingestion.pyingestion.os.path.isdir")
    def test_resume_deletes_state_on_success(
        self, mock_isdir, mock_exists, mock_listdir, resume_setup
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": resume_setup.options.BASE_PATH,
            "output_file": resume_setup.options.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": [],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(resume_setup.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield (1, 1, "raw text")

        resume_setup.mock_parser.process_file.side_effect = mock_process_file
        resume_setup.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        controller = PyIngestion(resume_setup.options, observer=mock_observer)
        resume_setup.options.RESUME = True

        success = controller.run(resume_setup.options)
        assert success is True

        # Check that CWD state file was deleted
        assert os.path.isfile(resume_setup.state_file_cwd) is False

    @patch("pyingestion.pyingestion.os.listdir")
    @patch("pyingestion.pyingestion.os.path.exists")
    @patch("pyingestion.pyingestion.os.path.isdir")
    def test_resume_preserves_state_on_cancel(
        self, mock_isdir, mock_exists, mock_listdir, resume_setup
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf", "file2.pdf"]
        mock_exists.side_effect = lambda p: True

        # Pre-create state file in CWD
        state_data = {
            "input_dir": resume_setup.options.BASE_PATH,
            "output_file": resume_setup.options.OUTPUT_CSV,
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(resume_setup.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        def mock_process_file(file_path, session, pages_per_unit=1):
            session.successful_pages += 1
            session.total_pages += 1
            yield (1, 1, "raw text")

        resume_setup.mock_parser.process_file.side_effect = mock_process_file
        resume_setup.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = True  # Cancelled!

        controller = PyIngestion(resume_setup.options, observer=mock_observer)
        resume_setup.options.RESUME = True

        success = controller.run(resume_setup.options)
        assert success is True

        # Check that CWD state file was NOT deleted (still exists)
        assert os.path.isfile(resume_setup.state_file_cwd) is True

    @patch("pyingestion.pyingestion.os.listdir")
    @patch("pyingestion.pyingestion.os.path.exists")
    @patch("pyingestion.pyingestion.os.path.isdir")
    def test_skip_blank_pages(
        self, mock_isdir, mock_exists, mock_listdir, resume_setup
    ):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["file1.pdf"]
        mock_exists.return_value = True

        # process_file yields a blank page first, then a non-blank page
        def mock_process_file(file_path, session, pages_per_unit=1):
            yield (1, 2, "   ")  # Blank page!
            yield (2, 2, "raw text")  # Valid page!

        resume_setup.mock_parser.process_file.side_effect = mock_process_file
        resume_setup.mock_regex.parse.return_value = {"field": "value"}

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False
        controller = PyIngestion(resume_setup.options, observer=mock_observer)

        success = controller.run(resume_setup.options)
        assert success is True

        # The mock_observer should have on_page_start called ONLY for the non-blank page (page 2)
        mock_observer.on_page_start.assert_called_once_with(2, 2)
        # Parse should only have been called with the valid page text
        resume_setup.mock_regex.parse.assert_called_once_with("raw text")
