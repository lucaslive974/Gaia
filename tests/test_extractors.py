import unittest
from unittest.mock import MagicMock, patch
from core.extractor import NativePdfExtractor


class TestExtractors(unittest.TestCase):
    @patch("core.extractor.PdfReader")
    def test_native_extractor_page_count(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [MagicMock(), MagicMock()]
        mock_pdf_reader.return_value = mock_reader_instance
        
        extractor = NativePdfExtractor()
        self.assertEqual(extractor.get_page_count("dummy.pdf"), 2)

    @patch("core.extractor.PdfReader")
    def test_native_extractor_extract_pages(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        page1 = MagicMock()
        page1.extract_text.return_value = "Native Page 1"
        page2 = MagicMock()
        page2.extract_text.return_value = "Native Page 2"
        mock_reader_instance.pages = [page1, page2]
        mock_pdf_reader.return_value = mock_reader_instance
        
        extractor = NativePdfExtractor()
        pages = list(extractor.extract_pages("dummy.pdf"))
        
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0], ("Native Page 1", "native"))
        self.assertEqual(pages[1], ("Native Page 2", "native"))

if __name__ == "__main__":
    unittest.main()
