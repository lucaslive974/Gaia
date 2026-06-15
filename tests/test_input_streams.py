import pytest
from unittest.mock import MagicMock, patch
from pyingestion import PdfInputStream, ExtractionSession


@patch("pyingestion.input_streams.PdfReader")
def test_native_parser_page_count(mock_pdf_reader):
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [MagicMock(), MagicMock()]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfInputStream()
    assert parser.get_page_count("dummy.pdf") == 2


@patch("pyingestion.input_streams.PdfReader")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_native_parser_orchestration(mock_isfile, mock_exists, mock_pdf_reader):
    mock_exists.return_value = True
    mock_isfile.return_value = True

    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "Page 1 Content"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page 2 Content"
    mock_reader_instance.pages = [page1, page2]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfInputStream(pages_per_unit=1)
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)

    pages = list(parser.read("dummy.pdf", session=session))

    assert len(pages) == 2
    assert pages[0] == "Page 1 Content"
    assert pages[1] == "Page 2 Content"
    assert session.total_pages == 2


@patch("pyingestion.input_streams.PdfReader")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_native_parser_orchestration_multi_page_units(
    mock_isfile, mock_exists, mock_pdf_reader
):
    mock_exists.return_value = True
    mock_isfile.return_value = True

    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "Page 1 Content"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page 2 Content"
    mock_reader_instance.pages = [page1, page2]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfInputStream(pages_per_unit=2)
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)

    pages = list(parser.read("dummy.pdf", session=session))

    assert len(pages) == 1
    assert pages[0] == "Page 1 Content\nPage 2 Content"
    assert session.total_pages == 2


@patch("pyingestion.input_streams.PdfReader")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_parser_cancellation_mid_file(mock_isfile, mock_exists, mock_pdf_reader):
    mock_exists.return_value = True
    mock_isfile.return_value = True

    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "page 1"
    page2 = MagicMock()
    page2.extract_text.return_value = "page 2"
    page3 = MagicMock()
    page3.extract_text.return_value = "page 3"
    mock_reader_instance.pages = [page1, page2, page3]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfInputStream(pages_per_unit=1)
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)

    gen = parser.read("dummy.pdf", session=session)
    first_page = next(gen)
    assert first_page == "page 1"

    session.is_cancelled = True

    pages_after_cancel = list(gen)
    assert len(pages_after_cancel) == 0


@patch("pyingestion.input_streams.PdfReader")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_parser_parameterless_session(mock_isfile, mock_exists, mock_pdf_reader):
    mock_exists.return_value = True
    mock_isfile.return_value = True

    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "valid text page"
    mock_reader_instance.pages = [page1]
    mock_pdf_reader.return_value = mock_reader_instance

    parser = PdfInputStream(pages_per_unit=1)
    pages = list(parser.read("dummy.pdf"))

    assert len(pages) == 1
    assert pages[0] == "valid text page"


def test_native_parser_accepts():
    parser = PdfInputStream()
    assert parser.accepts("test.pdf") is True
    assert parser.accepts("test.PDF") is True
    assert parser.accepts("test.txt") is False
    assert parser.accepts("test.pdf.docx") is False


from pyingestion import DocxInputStream


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

    parser = DocxInputStream()
    assert parser.get_page_count("dummy.docx") == 1


@patch("docx.Document")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_docx_parser_orchestration(mock_isfile, mock_exists, mock_docx_document):
    mock_exists.return_value = True
    mock_isfile.return_value = True

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

    parser = DocxInputStream(pages_per_unit=1)
    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    session = ExtractionSession(mock_observer)

    pages = list(parser.read("dummy.docx", session=session))
    assert len(pages) == 2
    assert pages[0] == "Paragraph 1 text"
    assert pages[1] == "Paragraph 2 text"
    assert session.total_pages == 2


def test_docx_parser_accepts():
    parser = DocxInputStream()
    assert parser.accepts("test.docx") is True
    assert parser.accepts("test.DOCX") is True
    assert parser.accepts("test.pdf") is False
    assert parser.accepts("test.txt") is False


from pyingestion import OcrInputStream


def test_ocr_parser_accepts():
    parser = OcrInputStream()
    assert parser.accepts("test.png") is True
    assert parser.accepts("test.JPG") is True
    assert parser.accepts("test.pdf") is True
    assert parser.accepts("test.docx") is False
    assert parser.accepts("test.txt") is False


@patch("shutil.which")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_ocr_parser_missing_tesseract(mock_isfile, mock_exists, mock_which):
    mock_exists.return_value = True
    mock_isfile.return_value = True
    mock_which.return_value = None  # tesseract not found
    parser = OcrInputStream()
    with pytest.raises(RuntimeError) as excinfo:
        list(parser.read("test.png"))
    assert "Tesseract OCR is not installed" in str(excinfo.value)


@patch("shutil.which")
def test_ocr_parser_missing_poppler_on_pdf(mock_which):
    # Tesseract is found, but poppler is not
    mock_which.side_effect = lambda cmd: (
        "/usr/bin/tesseract" if cmd == "tesseract" else None
    )
    parser = OcrInputStream()
    with pytest.raises(RuntimeError) as excinfo:
        parser.get_page_count("test.pdf")
    assert "Poppler (pdftoppm/pdfinfo) is not installed" in str(excinfo.value)


@patch("shutil.which")
@patch("PIL.Image.open")
@patch("pytesseract.image_to_string")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_ocr_parser_image_process(
    mock_isfile, mock_exists, mock_ocr, mock_image_open, mock_which
):
    mock_exists.return_value = True
    mock_isfile.return_value = True
    mock_which.return_value = "/usr/bin/tesseract"
    mock_image_open.return_value.__enter__.return_value = MagicMock()
    mock_ocr.return_value = "extracted image text"

    parser = OcrInputStream()
    session = ExtractionSession()
    results = list(parser.read("test.jpg", session=session))

    assert len(results) == 1
    assert results[0] == "extracted image text"
    assert session.total_pages == 1


@patch("shutil.which")
@patch("pdf2image.pdfinfo_from_path")
@patch("pdf2image.convert_from_path")
@patch("pytesseract.image_to_string")
@patch("pyingestion.input_stream.os.path.exists")
@patch("pyingestion.input_stream.os.path.isfile")
def test_ocr_parser_pdf_process_lazy(
    mock_isfile, mock_exists, mock_ocr, mock_convert, mock_pdfinfo, mock_which
):
    mock_exists.return_value = True
    mock_isfile.return_value = True
    mock_which.return_value = "/usr/bin/some_bin"
    mock_pdfinfo.return_value = {"Pages": 2}
    mock_convert.return_value = [MagicMock()]
    mock_ocr.side_effect = ["page 1 text", "page 2 text"]

    parser = OcrInputStream(pages_per_unit=1)
    session = ExtractionSession()
    results = list(parser.read("test.pdf", session=session))

    assert len(results) == 2
    assert results[0] == "page 1 text"
    assert results[1] == "page 2 text"
    assert session.total_pages == 2

    # Check lazy page-by-page calls
    assert mock_convert.call_count == 2
    mock_convert.assert_any_call("test.pdf", first_page=1, last_page=1, dpi=150)
    mock_convert.assert_any_call("test.pdf", first_page=2, last_page=2, dpi=150)
