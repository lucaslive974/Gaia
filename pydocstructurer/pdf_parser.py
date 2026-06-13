from typing import Generator
from pypdf import PdfReader
from pydocstructurer.extraction_session import ExtractionSession
from pydocstructurer.parser import Parser


class PdfParser(Parser):
    """
    PDF parser using layout-based text extraction from pypdf.
    """

    def accepts(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def get_page_count(self, pdf_path: str) -> int:
        """
        Returns the total number of pages in the PDF file.
        """
        reader = PdfReader(pdf_path)
        return len(reader.pages)

    def _extract_single_page(self, reader: PdfReader, page_num: int) -> str:
        if page_num < 1 or page_num > len(reader.pages):
            return ""
        page = reader.pages[page_num - 1]
        return page.extract_text(extraction_mode="layout") or ""

    def process_file(
        self,
        file_path: str,
        session: ExtractionSession | None = None,
        pages_per_unit: int = 1,
    ) -> Generator[tuple[int, int, str], None, None]:
        """
        Processes the PDF file page-by-page or in chunks, yielding
        (unit_index, total_units, unit_text).
        """
        from pydocstructurer.extraction_session import NoOpExtractionSession

        session = session or NoOpExtractionSession()

        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        session.total_pages += total_pages

        # Extract and group pages lazily
        total_units = (total_pages + pages_per_unit - 1) // pages_per_unit
        unit_pages = []
        unit_index = 1

        for page_num in range(1, total_pages + 1):
            if session.is_cancelled:
                break

            page_text = self._extract_single_page(reader, page_num)
            unit_pages.append(page_text)

            if len(unit_pages) == pages_per_unit:
                yield unit_index, total_units, "\n".join(unit_pages)
                unit_pages = []
                unit_index += 1

        if unit_pages and not session.is_cancelled:
            yield unit_index, total_units, "\n".join(unit_pages)

