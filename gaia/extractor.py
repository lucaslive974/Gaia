from abc import ABC, abstractmethod
from typing import Generator
from pypdf import PdfReader


class BasePdfExtractor(ABC):
    @abstractmethod
    def get_page_count(self, pdf_path: str) -> int:
        """
        Returns the total number of pages in the PDF file.
        """
        pass

    @abstractmethod
    def extract_pages(self, pdf_path: str) -> Generator[str, None, None]:
        """
        Yields the text content of each page sequentially.
        """
        pass


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

    def extract_pages(self, pdf_path: str) -> Generator[str, None, None]:
        reader = PdfReader(pdf_path)
        for page_num in range(1, len(reader.pages) + 1):
            yield self._extract_single_page(reader, page_num)


