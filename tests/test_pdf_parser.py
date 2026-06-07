import unittest
from unittest.mock import MagicMock, patch
from gaia import NativePdfParser, ExtractionSession


class TestPdfParser(unittest.TestCase):
    @patch("gaia.pdf_parser.PdfReader")
    def test_native_parser_page_count(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [MagicMock(), MagicMock()]
        mock_pdf_reader.return_value = mock_reader_instance

        parser = NativePdfParser()
        self.assertEqual(parser.get_page_count("dummy.pdf"), 2)

    @patch("gaia.pdf_parser.PdfReader")
    def test_native_parser_orchestration(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        page1 = MagicMock()
        page1.extract_text.return_value = "Page 1 Content"
        page2 = MagicMock()
        page2.extract_text.return_value = "Page 2 Content"
        mock_reader_instance.pages = [page1, page2]
        mock_pdf_reader.return_value = mock_reader_instance

        parser = NativePdfParser()
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False
        session = ExtractionSession(mock_observer)

        pages = list(parser.process_file("dummy.pdf", session=session, pages_per_unit=1))

        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0][2], "Page 1 Content")
        self.assertEqual(pages[1][2], "Page 2 Content")
        self.assertEqual(session.total_pages, 2)

    @patch("gaia.pdf_parser.PdfReader")
    def test_native_parser_orchestration_multi_page_units(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        page1 = MagicMock()
        page1.extract_text.return_value = "Page 1 Content"
        page2 = MagicMock()
        page2.extract_text.return_value = "Page 2 Content"
        mock_reader_instance.pages = [page1, page2]
        mock_pdf_reader.return_value = mock_reader_instance

        parser = NativePdfParser()
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False
        session = ExtractionSession(mock_observer)

        pages = list(parser.process_file("dummy.pdf", session=session, pages_per_unit=2))

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0][2], "Page 1 Content\nPage 2 Content")
        self.assertEqual(session.total_pages, 2)

    @patch("gaia.pdf_parser.PdfReader")
    def test_parser_cancellation_mid_file(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        page1 = MagicMock()
        page1.extract_text.return_value = "page 1"
        page2 = MagicMock()
        page2.extract_text.return_value = "page 2"
        page3 = MagicMock()
        page3.extract_text.return_value = "page 3"
        mock_reader_instance.pages = [page1, page2, page3]
        mock_pdf_reader.return_value = mock_reader_instance

        parser = NativePdfParser()
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False
        session = ExtractionSession(mock_observer)

        gen = parser.process_file("dummy.pdf", session=session, pages_per_unit=1)
        first_page = next(gen)
        self.assertEqual(first_page[2], "page 1")

        session.is_cancelled = True

        pages_after_cancel = list(gen)
        self.assertEqual(len(pages_after_cancel), 0)

    @patch("gaia.pdf_parser.PdfReader")
    def test_parser_parameterless_session(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        page1 = MagicMock()
        page1.extract_text.return_value = "valid text page"
        mock_reader_instance.pages = [page1]
        mock_pdf_reader.return_value = mock_reader_instance

        parser = NativePdfParser()
        pages = list(parser.process_file("dummy.pdf"))

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0][2], "valid text page")


if __name__ == "__main__":
    unittest.main()
