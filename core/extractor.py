from abc import ABC, abstractmethod
from typing import Generator
from pypdf import PdfReader
from core.cnn_ai_model import CnnAiModel, Pytesseract
from pdf2image import pdfinfo_from_path, convert_from_path


class BasePdfExtractor(ABC):
    @abstractmethod
    def get_page_count(self, pdf_path: str) -> int:
        """
        Returns the total number of pages in the PDF file.
        """
        pass

    @abstractmethod
    def extract_pages(self, pdf_path: str) -> Generator[tuple[str, str], None, None]:
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
        images = convert_from_path(
            pdf_path, dpi=300, first_page=page_num, last_page=page_num
        )
        if not images:
            return ""
        image = images[0]
        # OCR process on the single image
        return self._cnn_ai_model.process_image(image)

    def extract_pages(self, pdf_path: str) -> Generator[tuple[str, str], None, None]:
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
        return page.extract_text(extraction_mode="layout") or ""

    def extract_pages(self, pdf_path: str) -> Generator[tuple[str, str], None, None]:
        reader = PdfReader(pdf_path)
        for page_num in range(1, len(reader.pages) + 1):
            yield self._extract_single_page(reader, page_num), "native"

