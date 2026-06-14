import pytest
from unittest.mock import MagicMock, patch
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


from pydocstructurer import OcrParser


def test_ocr_parser_accepts():
    parser = OcrParser()
    assert parser.accepts("test.png") is True
    assert parser.accepts("test.JPG") is True
    assert parser.accepts("test.pdf") is True
    assert parser.accepts("test.docx") is False
    assert parser.accepts("test.txt") is False


@patch("shutil.which")
def test_ocr_parser_missing_tesseract(mock_which):
    mock_which.return_value = None  # tesseract not found
    parser = OcrParser()
    with pytest.raises(RuntimeError) as excinfo:
        list(parser.process_file("test.png"))
    assert "Tesseract OCR is not installed" in str(excinfo.value)


@patch("shutil.which")
def test_ocr_parser_missing_poppler_on_pdf(mock_which):
    # Tesseract is found, but poppler is not
    mock_which.side_effect = lambda cmd: (
        "/usr/bin/tesseract" if cmd == "tesseract" else None
    )
    parser = OcrParser()
    with pytest.raises(RuntimeError) as excinfo:
        parser.get_page_count("test.pdf")
    assert "Poppler (pdftoppm/pdfinfo) is not installed" in str(excinfo.value)


@patch("shutil.which")
@patch("PIL.Image.open")
@patch("pytesseract.image_to_string")
def test_ocr_parser_image_process(mock_ocr, mock_image_open, mock_which):
    mock_which.return_value = "/usr/bin/tesseract"
    mock_image_open.return_value.__enter__.return_value = MagicMock()
    mock_ocr.return_value = "extracted image text"

    parser = OcrParser()
    session = ExtractionSession()
    results = list(parser.process_file("test.jpg", session=session))

    assert len(results) == 1
    assert results[0] == (1, 1, "extracted image text")
    assert session.total_pages == 1


@patch("shutil.which")
@patch("pdf2image.pdfinfo_from_path")
@patch("pdf2image.convert_from_path")
@patch("pytesseract.image_to_string")
def test_ocr_parser_pdf_process_lazy(mock_ocr, mock_convert, mock_pdfinfo, mock_which):
    mock_which.return_value = "/usr/bin/some_bin"
    mock_pdfinfo.return_value = {"Pages": 2}
    mock_convert.return_value = [MagicMock()]
    mock_ocr.side_effect = ["page 1 text", "page 2 text"]

    parser = OcrParser()
    session = ExtractionSession()
    results = list(parser.process_file("test.pdf", session=session, pages_per_unit=1))

    assert len(results) == 2
    assert results[0] == (1, 2, "page 1 text")
    assert results[1] == (2, 2, "page 2 text")
    assert session.total_pages == 2

    # Check lazy page-by-page calls
    assert mock_convert.call_count == 2
    mock_convert.assert_any_call("test.pdf", first_page=1, last_page=1, dpi=150)
    mock_convert.assert_any_call("test.pdf", first_page=2, last_page=2, dpi=150)
