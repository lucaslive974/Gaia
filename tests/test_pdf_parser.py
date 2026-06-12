from unittest.mock import MagicMock, patch
import pytest
from gaia import PdfParser, ExtractionSession


@patch("gaia.pdf_parser.PdfReader")
def test_native_parser_page_count(mock_pdf_reader):
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [MagicMock(), MagicMock()]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfParser()
    assert parser.get_page_count("dummy.pdf") == 2


@patch("gaia.pdf_parser.PdfReader")
def test_native_parser_orchestration(mock_pdf_reader):
    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "Page 1 Content"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page 2 Content"
    mock_reader_instance.pages = [page1, page2]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfParser()
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)

    pages = list(parser.process_file("dummy.pdf", session=session, pages_per_unit=1))

    assert len(pages) == 2
    assert pages[0][2] == "Page 1 Content"
    assert pages[1][2] == "Page 2 Content"
    assert session.total_pages == 2


@patch("gaia.pdf_parser.PdfReader")
def test_native_parser_orchestration_multi_page_units(mock_pdf_reader):
    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "Page 1 Content"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page 2 Content"
    mock_reader_instance.pages = [page1, page2]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfParser()
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)

    pages = list(parser.process_file("dummy.pdf", session=session, pages_per_unit=2))

    assert len(pages) == 1
    assert pages[0][2] == "Page 1 Content\nPage 2 Content"
    assert session.total_pages == 2


@patch("gaia.pdf_parser.PdfReader")
def test_parser_cancellation_mid_file(mock_pdf_reader):
    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "page 1"
    page2 = MagicMock()
    page2.extract_text.return_value = "page 2"
    page3 = MagicMock()
    page3.extract_text.return_value = "page 3"
    mock_reader_instance.pages = [page1, page2, page3]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfParser()
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)

    gen = parser.process_file("dummy.pdf", session=session, pages_per_unit=1)
    first_page = next(gen)
    assert first_page[2] == "page 1"

    session.is_cancelled = True

    pages_after_cancel = list(gen)
    assert len(pages_after_cancel) == 0


@patch("gaia.pdf_parser.PdfReader")
def test_parser_parameterless_session(mock_pdf_reader):
    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "valid text page"
    mock_reader_instance.pages = [page1]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfParser()
    pages = list(parser.process_file("dummy.pdf"))

    assert len(pages) == 1
    assert pages[0][2] == "valid text page"


def test_native_parser_accepts():
    parser = PdfParser()
    assert parser.accepts("test.pdf") is True
    assert parser.accepts("test.PDF") is True
    assert parser.accepts("test.txt") is False
    assert parser.accepts("test.pdf.docx") is False
