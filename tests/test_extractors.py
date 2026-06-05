import unittest
from unittest.mock import MagicMock, patch
from core.extractor import OcrPdfExtractor, NativePdfExtractor


class TestExtractors(unittest.TestCase):
    @patch("core.extractor.pdfinfo_from_path")
    def test_ocr_extractor_page_count(self, mock_pdfinfo):
        mock_pdfinfo.return_value = {"Pages": 42}
        extractor = OcrPdfExtractor()
        page_count = extractor.get_page_count("dummy.pdf")
        self.assertEqual(page_count, 42)
        mock_pdfinfo.assert_called_once_with("dummy.pdf")

    @patch("core.extractor.pdfinfo_from_path")
    @patch("core.extractor.convert_from_path")
    def test_ocr_extractor_extract_pages(self, mock_convert, mock_pdfinfo):
        mock_pdfinfo.return_value = {"Pages": 2}
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        
        mock_cnn = MagicMock()
        mock_cnn.process_image.return_value = "Page Text"
        
        extractor = OcrPdfExtractor(cnn_ai_model=mock_cnn)
        pages = list(extractor.extract_pages("dummy.pdf"))
        
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0], ("Page Text", "ocr"))
        self.assertEqual(pages[1], ("Page Text", "ocr"))
        self.assertEqual(mock_convert.call_count, 2)
        mock_cnn.process_image.assert_called_with(mock_image)

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
