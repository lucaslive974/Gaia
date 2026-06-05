import unittest
from unittest.mock import MagicMock, patch
from core.extractor import OcrPdfExtractor, NativePdfExtractor, FallbackPdfExtractor


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

    @patch("core.extractor.PdfReader")
    def test_fallback_extractor_page_count(self, mock_pdf_reader):
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [MagicMock(), MagicMock(), MagicMock()]
        mock_pdf_reader.return_value = mock_reader_instance
        
        extractor = FallbackPdfExtractor()
        self.assertEqual(extractor.get_page_count("dummy.pdf"), 3)

    @patch("core.extractor.PdfReader")
    @patch("core.extractor.OcrPdfExtractor._extract_single_page")
    def test_fallback_extractor_mixed_pages(self, mock_extract_ocr, mock_pdf_reader):
        # Setup mock reader for native extraction
        mock_reader_instance = MagicMock()
        
        page1 = MagicMock()
        # Page 1: Native text is long enough (>= threshold of 20)
        page1.extract_text.return_value = "This is a very long native text page that should not trigger OCR."
        
        page2 = MagicMock()
        # Page 2: Native text is empty/too short
        page2.extract_text.return_value = "Short"
        
        page3 = MagicMock()
        # Page 3: Native text is None
        page3.extract_text.return_value = None
        
        mock_reader_instance.pages = [page1, page2, page3]
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Setup mock OCR extractor
        mock_extract_ocr.side_effect = lambda pdf_path, page_num: f"OCR Text for Page {page_num}"
        
        extractor = FallbackPdfExtractor(min_char_threshold=20)
        pages = list(extractor.extract_pages("dummy.pdf"))
        
        self.assertEqual(len(pages), 3)
        # Page 1: Native text preferred
        self.assertEqual(pages[0], ("This is a very long native text page that should not trigger OCR.", "native"))
        # Page 2: Fell back to OCR because "Short" length (5) < threshold (20)
        self.assertEqual(pages[1], ("OCR Text for Page 2", "ocr"))
        # Page 3: Fell back to OCR because None/empty < threshold (20)
        self.assertEqual(pages[2], ("OCR Text for Page 3", "ocr"))
        
        # Verify OCR was only called for page 2 and page 3, not page 1
        self.assertEqual(mock_extract_ocr.call_count, 2)
        mock_extract_ocr.assert_any_call("dummy.pdf", 2)
        mock_extract_ocr.assert_any_call("dummy.pdf", 3)


if __name__ == "__main__":
    unittest.main()
