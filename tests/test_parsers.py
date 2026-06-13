from unittest.mock import MagicMock, patch
import pytest
from pydocstructurer import PdfParser, ExtractionSession


@patch("pydocstructurer.parsers.PdfReader")
def test_native_parser_page_count(mock_pdf_reader):
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [MagicMock(), MagicMock()]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfParser()
    assert parser.get_page_count("dummy.pdf") == 2


@patch("pydocstructurer.parsers.PdfReader")
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


@patch("pydocstructurer.parsers.PdfReader")
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


@patch("pydocstructurer.parsers.PdfReader")
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


@patch("pydocstructurer.parsers.PdfReader")
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


from pydocstructurer import DocxParser

@patch("docx.Document")
def test_docx_parser_page_count(mock_docx_document):
    mock_doc_instance = MagicMock()
    mock_p = MagicMock()
    mock_p.tag = "p"
    mock_p._element = MagicMock()
    mock_p._element.xml = "<w:p></w:p>"
    mock_p.paragraph_format.page_break_before = False
    mock_p.text = "Hello world"
    
    mock_doc_instance.element.body.iterchildren.return_value = [mock_p]
    mock_docx_document.return_value = mock_doc_instance
    
    parser = DocxParser()
    assert parser.get_page_count("dummy.docx") == 1


@patch("docx.Document")
def test_docx_parser_orchestration(mock_docx_document):
    mock_doc_instance = MagicMock()
    
    mock_p1 = MagicMock()
    mock_p1.tag = "p"
    mock_p1._element = MagicMock()
    mock_p1._element.xml = "<w:p></w:p>"
    mock_p1.paragraph_format.page_break_before = False
    mock_p1.text = "Paragraph 1 text"
    
    mock_p2 = MagicMock()
    mock_p2.tag = "p"
    mock_p2._element = MagicMock()
    mock_p2._element.xml = '<w:p><w:r><w:br type="page"/></w:r></w:p>'
    mock_p2.paragraph_format.page_break_before = True
    mock_p2.text = "Paragraph 2 text"
    
    mock_doc_instance.element.body.iterchildren.return_value = [mock_p1, mock_p2]
    mock_docx_document.return_value = mock_doc_instance
    
    parser = DocxParser()
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)
    
    pages = list(parser.process_file("dummy.docx", session=session, pages_per_unit=1))
    assert len(pages) == 2
    assert pages[0][2] == "Paragraph 1 text"
    assert pages[1][2] == "Paragraph 2 text"
    assert session.total_pages == 2


def test_docx_parser_accepts():
    parser = DocxParser()
    assert parser.accepts("test.docx") is True
    assert parser.accepts("test.DOCX") is True
    assert parser.accepts("test.pdf") is False
    assert parser.accepts("test.txt") is False
