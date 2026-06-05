from abc import ABC, abstractmethod
from typing import Generator, Callable
from pdf2image import pdfinfo_from_path, convert_from_path
from pypdf import PdfReader
from core.cnn_ai_model import CnnAiModel, Pytesseract


class BasePdfExtractor(ABC):
    @abstractmethod
    def get_page_count(self, pdf_path: str) -> int:
        """
        Returns the total number of pages in the PDF file.
        """
        pass

    @abstractmethod
    def extract_pages(
        self,
        pdf_path: str,
        validator: Callable[[str], bool] | None = None
    ) -> Generator[tuple[str, str], None, None]:
        """
        Yields the text content of each page and the method used (text, method) sequentially.
        """
        pass


class OcrPdfExtractor(BasePdfExtractor):
    """
    Page-by-page PDF text extractor using Tesseract OCR.
    """
    def __init__(self, cnn_ai_model: CnnAiModel | None = None):
        self._cnn_ai_model = cnn_ai_model or Pytesseract()

    def get_page_count(self, pdf_path: str) -> int:
        info = pdfinfo_from_path(pdf_path)
        return int(info.get("Pages", 0))

    def _extract_single_page(self, pdf_path: str, page_num: int) -> str:
        # Convert only a single page to image to prevent RAM exhaustion
        images = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
        if not images:
            return ""
        image = images[0]
        # OCR process on the single image
        return self._cnn_ai_model.process_image(image)

    def extract_pages(
        self,
        pdf_path: str,
        validator: Callable[[str], bool] | None = None
    ) -> Generator[tuple[str, str], None, None]:
        total_pages = self.get_page_count(pdf_path)
        for page_num in range(1, total_pages + 1):
            yield self._extract_single_page(pdf_path, page_num), "ocr"


class NativePdfExtractor(BasePdfExtractor):
    """
    Page-by-page native PDF text extractor using pypdf.
    """
    def get_page_count(self, pdf_path: str) -> int:
        reader = PdfReader(pdf_path)
        return len(reader.pages)

    def _extract_single_page(self, reader: PdfReader, page_num: int) -> str:
        if page_num < 1 or page_num > len(reader.pages):
            return ""
        page = reader.pages[page_num - 1]
        return page.extract_text() or ""

    def extract_pages(
        self,
        pdf_path: str,
        validator: Callable[[str], bool] | None = None
    ) -> Generator[tuple[str, str], None, None]:
        reader = PdfReader(pdf_path)
        for page_num in range(1, len(reader.pages) + 1):
            yield self._extract_single_page(reader, page_num), "native"


class FallbackPdfExtractor(BasePdfExtractor):
    """
    Combines NativePdfExtractor and OcrPdfExtractor.
    For each page:
      1. Tries to extract text using NativePdfExtractor first.
      2. If the extracted text has length below threshold (suggesting a scanned image PDF page),
         it falls back to OcrPdfExtractor ONLY for that specific page.
    """
    def __init__(self, min_char_threshold: int = 20, ocr_extractor: OcrPdfExtractor | None = None, native_extractor: NativePdfExtractor | None = None):
        self.min_char_threshold = min_char_threshold
        self._ocr_extractor = ocr_extractor or OcrPdfExtractor()
        self._native_extractor = native_extractor or NativePdfExtractor()

    def get_page_count(self, pdf_path: str) -> int:
        return self._native_extractor.get_page_count(pdf_path)

    def extract_pages(
        self,
        pdf_path: str,
        validator: Callable[[str], bool] | None = None
    ) -> Generator[tuple[str, str], None, None]:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        for page_num in range(1, total_pages + 1):
            # 1. Tentar extração nativa
            text = self._native_extractor._extract_single_page(reader, page_num)
            method = "native"
            
            # 2. Se falhar no limite de caracteres ou no validador, usar OCR
            should_ocr = len(text.strip()) < self.min_char_threshold
            if not should_ocr and validator is not None:
                should_ocr = not validator(text)
                
            if should_ocr:
                text = self._ocr_extractor._extract_single_page(pdf_path, page_num)
                method = "ocr"
                
            yield text, method