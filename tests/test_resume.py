import json
import os
from unittest.mock import MagicMock, patch

import pytest

from pyingestion.extraction_session import ExtractionSession, FileExtractionSession
from pyingestion.pyingestion import PyIngestion


class TestResumeSession:
    @pytest.fixture
    def resume_setup(self, tmp_path):
        # Mock getcwd to return our tmp_path directory to avoid creating files in actual workspace CWD
        cwd_patcher = patch("os.getcwd", return_value=str(tmp_path))
        cwd_patcher.start()

        state_file_cwd = os.path.join(str(tmp_path), ".gaia_resume.json")
        input_dir = os.path.join(tmp_path, "dummy_dir")
        os.makedirs(input_dir, exist_ok=True)
        state_file_input = os.path.join(input_dir, ".gaia_resume.json")

        class Context:
            input_dir: str = ""
            state_file_cwd: str = ""
            state_file_input: str = ""

        ctx = Context()
        ctx.input_dir = input_dir
        ctx.state_file_cwd = state_file_cwd
        ctx.state_file_input = state_file_input

        yield ctx
        cwd_patcher.stop()

    def test_resume_skips_processed_files(self, resume_setup):
        # Pre-create state file in CWD
        state_data = {
            "input_dir": resume_setup.input_dir,
            "output_file": "output.csv",
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

        restored_state = FileExtractionSession.load(resume_setup.input_dir)
        assert restored_state is not None

        session = ExtractionSession()
        session.bus.on("page.started", mock_observer.on_page_start)
        if mock_observer.is_cancelled:
            session.is_cancelled = True
        from typing import cast

        session.processed_files = cast(list[str], restored_state["processed_files"])
        session.successful_pages = cast(int, restored_state["successful_pages"])
        session.failed_pages = cast(int, restored_state["failed_pages"])
        session.total_pages = cast(int, restored_state["total_pages"])

        # Mock input stream
        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream(pages_per_unit=1)

        # Patch _find_files to return both files
        with patch.object(
            PdfInputStream, "_find_files", return_value=["file1.pdf", "file2.pdf"]
        ):
            # Mock read's inner processing or mock reader
            with patch("pyingestion.input_streams.PdfReader") as mock_pdf_reader:
                mock_reader_instance = MagicMock()
                page = MagicMock()
                page.extract_text.return_value = "raw text"
                mock_reader_instance.pages = [page]
                mock_pdf_reader.return_value = mock_reader_instance

                # Mock transform and output
                transform_stream = MagicMock()
                transform_stream.transform.return_value = {"field": "val"}
                output_stream = MagicMock()

                controller = PyIngestion()
                success = controller.process(
                    source=resume_setup.input_dir,
                    input_stream=input_stream,
                    transform_stream=transform_stream,
                    output_stream=output_stream,
                    session=session,
                )

                assert success is True
                # file1.pdf is skipped, only file2.pdf is processed (1 call to PdfReader for file2.pdf)
                assert mock_pdf_reader.call_count == 1

    def test_resume_loads_correct_state_counters(self, resume_setup):
        state_data = {
            "input_dir": resume_setup.input_dir,
            "output_file": "output.csv",
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

        restored_state = FileExtractionSession.load(resume_setup.input_dir)
        assert restored_state is not None
        session = ExtractionSession()
        session.bus.on("page.started", mock_observer.on_page_start)
        if mock_observer.is_cancelled:
            session.is_cancelled = True
        from typing import cast

        session.processed_files = cast(list[str], restored_state["processed_files"])
        session.successful_pages = cast(int, restored_state["successful_pages"])
        session.failed_pages = cast(int, restored_state["failed_pages"])
        session.total_pages = cast(int, restored_state["total_pages"])

        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream(pages_per_unit=1)

        with (
            patch.object(
                PdfInputStream, "_find_files", return_value=["file1.pdf", "file2.pdf"]
            ),
            patch("pyingestion.input_streams.PdfReader") as mock_pdf_reader,
        ):
            mock_reader_instance = MagicMock()
            page = MagicMock()
            page.extract_text.return_value = "raw text"
            mock_reader_instance.pages = [page]
            mock_pdf_reader.return_value = mock_reader_instance

            transform_stream = MagicMock()
            transform_stream.transform.return_value = {"field": "val"}
            output_stream = MagicMock()

            controller = PyIngestion()
            # Before process runs, counters are restored:
            assert session.successful_pages == 10
            assert session.failed_pages == 2
            assert session.total_pages == 12

            success = controller.process(
                source=resume_setup.input_dir,
                input_stream=input_stream,
                transform_stream=transform_stream,
                output_stream=output_stream,
                session=session,
            )
            assert success is True

    def test_resume_saves_updated_state_after_each_file(self, resume_setup):
        state_data = {
            "input_dir": resume_setup.input_dir,
            "output_file": "output.csv",
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

        restored_state = FileExtractionSession.load(resume_setup.input_dir)
        assert restored_state is not None
        session = FileExtractionSession()
        session.bus.on("page.started", mock_observer.on_page_start)
        if mock_observer.is_cancelled:
            session.is_cancelled = True
        from typing import cast

        session.processed_files = cast(list[str], restored_state["processed_files"])
        session.successful_pages = cast(int, restored_state["successful_pages"])
        session.failed_pages = cast(int, restored_state["failed_pages"])
        session.total_pages = cast(int, restored_state["total_pages"])

        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream(pages_per_unit=1)

        with (
            patch.object(
                PdfInputStream, "_find_files", return_value=["file1.pdf", "file2.pdf"]
            ),
            patch("pyingestion.input_streams.PdfReader") as mock_pdf_reader,
        ):
            mock_reader_instance = MagicMock()
            page = MagicMock()
            page.extract_text.return_value = "raw text"
            mock_reader_instance.pages = [page]
            mock_pdf_reader.return_value = mock_reader_instance

            transform_stream = MagicMock()
            transform_stream.transform.return_value = {"field": "val"}
            output_stream = MagicMock()

            with patch("pyingestion.extraction_session.open", create=True) as mock_open:
                controller = PyIngestion()
                success = controller.process(
                    source=resume_setup.input_dir,
                    input_stream=input_stream,
                    transform_stream=transform_stream,
                    output_stream=output_stream,
                    session=session,
                )
                assert success is True
                # Verify state file save was called
                mock_open.assert_any_call(
                    resume_setup.state_file_cwd, "w", encoding="utf-8"
                )
                mock_open.assert_any_call(
                    resume_setup.state_file_input, "w", encoding="utf-8"
                )

    def test_resume_deletes_state_on_success(self, resume_setup):
        state_data = {
            "input_dir": resume_setup.input_dir,
            "output_file": "output.csv",
            "regex_file": "/dummy/regex.json",
            "processed_files": [],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(resume_setup.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        restored_state = FileExtractionSession.load(resume_setup.input_dir)
        assert restored_state is not None
        session = FileExtractionSession()
        session.bus.on("page.started", mock_observer.on_page_start)
        if mock_observer.is_cancelled:
            session.is_cancelled = True
        from typing import cast

        session.processed_files = cast(list[str], restored_state["processed_files"])
        session.successful_pages = cast(int, restored_state["successful_pages"])
        session.failed_pages = cast(int, restored_state["failed_pages"])
        session.total_pages = cast(int, restored_state["total_pages"])

        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream(pages_per_unit=1)

        with patch.object(PdfInputStream, "_find_files", return_value=["file1.pdf"]):
            with patch("pyingestion.input_streams.PdfReader") as mock_pdf_reader:
                mock_reader_instance = MagicMock()
                page = MagicMock()
                page.extract_text.return_value = "raw text"
                mock_reader_instance.pages = [page]
                mock_pdf_reader.return_value = mock_reader_instance

                transform_stream = MagicMock()
                transform_stream.transform.return_value = {"field": "val"}
                output_stream = MagicMock()

                controller = PyIngestion()
                success = controller.process(
                    source=resume_setup.input_dir,
                    input_stream=input_stream,
                    transform_stream=transform_stream,
                    output_stream=output_stream,
                    session=session,
                )
                assert success is True
                # Check that CWD state file was deleted
                assert os.path.isfile(resume_setup.state_file_cwd) is False

    def test_resume_preserves_state_on_cancel(self, resume_setup):
        state_data = {
            "input_dir": resume_setup.input_dir,
            "output_file": "output.csv",
            "regex_file": "/dummy/regex.json",
            "processed_files": ["file1.pdf"],
            "successful_pages": 10,
            "failed_pages": 2,
            "total_pages": 12,
        }
        with open(resume_setup.state_file_cwd, "w", encoding="utf-8") as sf:
            json.dump(state_data, sf)

        mock_observer = MagicMock()
        mock_observer.is_cancelled = True  # Cancelled!

        restored_state = FileExtractionSession.load(resume_setup.input_dir)
        assert restored_state is not None
        session = ExtractionSession()
        session.bus.on("page.started", mock_observer.on_page_start)
        if mock_observer.is_cancelled:
            session.is_cancelled = True
        from typing import cast

        session.processed_files = cast(list[str], restored_state["processed_files"])
        session.successful_pages = cast(int, restored_state["successful_pages"])
        session.failed_pages = cast(int, restored_state["failed_pages"])
        session.total_pages = cast(int, restored_state["total_pages"])

        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream(pages_per_unit=1)

        with (
            patch.object(
                PdfInputStream, "_find_files", return_value=["file1.pdf", "file2.pdf"]
            ),
            patch("pyingestion.input_streams.PdfReader") as mock_pdf_reader,
        ):
            mock_reader_instance = MagicMock()
            page = MagicMock()
            page.extract_text.return_value = "raw text"
            mock_reader_instance.pages = [page]
            mock_pdf_reader.return_value = mock_reader_instance

            transform_stream = MagicMock()
            transform_stream.transform.return_value = {"field": "val"}
            output_stream = MagicMock()

            controller = PyIngestion()
            success = controller.process(
                source=resume_setup.input_dir,
                input_stream=input_stream,
                transform_stream=transform_stream,
                output_stream=output_stream,
                session=session,
            )
            assert success is True
            # Check that CWD state file still exists (not deleted since cancelled)
            assert os.path.isfile(resume_setup.state_file_cwd) is True

    def test_skip_blank_pages(self, resume_setup):
        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream(pages_per_unit=1)

        with patch.object(PdfInputStream, "_find_files", return_value=["file1.pdf"]):
            with patch("pyingestion.input_streams.PdfReader") as mock_pdf_reader:
                mock_reader_instance = MagicMock()
                page1 = MagicMock()
                page1.extract_text.return_value = "   "  # Blank page!
                page2 = MagicMock()
                page2.extract_text.return_value = "raw text"  # Valid page!
                mock_reader_instance.pages = [page1, page2]
                mock_pdf_reader.return_value = mock_reader_instance

                transform_stream = MagicMock()
                transform_stream.transform.return_value = {"field": "value"}
                output_stream = MagicMock()

                mock_observer = MagicMock()
                mock_observer.is_cancelled = False
                session = ExtractionSession()
                session.bus.on("page.started", mock_observer.on_page_start)
                if mock_observer.is_cancelled:
                    session.is_cancelled = True

                controller = PyIngestion()
                success = controller.process(
                    source=resume_setup.input_dir,
                    input_stream=input_stream,
                    transform_stream=transform_stream,
                    output_stream=output_stream,
                    session=session,
                )
                assert success is True

                # The mock_observer should have on_page_start called ONLY for the non-blank page (page 2)
                mock_observer.on_page_start.assert_called_once_with(
                    session=session, page_index=2, total_pages=2
                )
                # Transform should only have been called with the valid page text
                transform_stream.transform.assert_called_once_with("raw text")

    def test_custom_error_handler(self, resume_setup):
        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream(pages_per_unit=1)

        errors_logged = []

        def my_error_handler(page_text, page_number, error_msg, extracted_data):
            errors_logged.append((page_text, page_number, error_msg, extracted_data))

        session = FileExtractionSession(error_handler=my_error_handler)

        with patch.object(PdfInputStream, "_find_files", return_value=["file1.pdf"]):
            with patch("pyingestion.input_streams.PdfReader") as mock_pdf_reader:
                mock_reader_instance = MagicMock()
                page = MagicMock()
                page.extract_text.return_value = "error page"
                mock_reader_instance.pages = [page]
                mock_pdf_reader.return_value = mock_reader_instance

                transform_stream = MagicMock()
                transform_stream.transform.side_effect = ValueError(
                    "custom transform error"
                )
                output_stream = MagicMock()

                controller = PyIngestion()
                success = controller.process(
                    source=resume_setup.input_dir,
                    input_stream=input_stream,
                    transform_stream=transform_stream,
                    output_stream=output_stream,
                    session=session,
                )
                assert success is True
                assert len(errors_logged) == 1
                assert errors_logged[0][0] == "error page"
                assert errors_logged[0][1] == 1
                assert "custom transform error" in errors_logged[0][2]
