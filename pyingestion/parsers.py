from typing import Generator
from pypdf import PdfReader
from pyingestion.extraction_session import ExtractionSession
from pyingestion.input_stream import InputStream


class PdfParser(InputStream):
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
        from pyingestion.extraction_session import NoOpExtractionSession

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


class DocxParser(InputStream):
    """
    DOCX parser using python-docx to extract text.
    """

    def accepts(self, file_path: str) -> bool:
        return file_path.lower().endswith(".docx")

    def _parse_pages(self, docx_path: str) -> list[str]:
        import docx
        from docx.text.paragraph import Paragraph
        from docx.table import Table as DocxTable

        doc = docx.Document(docx_path)
        pages = []
        current_page_text = []

        def has_page_break(p: Paragraph) -> bool:
            if p.paragraph_format.page_break_before:
                return True
            p_xml = p._element.xml
            if "w:br" in p_xml and 'type="page"' in p_xml:
                return True
            return False

        def get_table_text(table: DocxTable) -> str:
            text_parts = []
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    cell_p_texts = [p.text for p in cell.paragraphs]
                    row_text.append(" ".join(cell_p_texts))
                text_parts.append(" | ".join(row_text))
            return "\n".join(text_parts)

        body_elm = doc.element.body
        for child in body_elm.iterchildren():
            if child.tag.endswith("p"):
                p = Paragraph(child, doc)
                p_text = p.text
                if has_page_break(p) and current_page_text:
                    pages.append("\n".join(current_page_text))
                    current_page_text = []
                current_page_text.append(p_text)
            elif child.tag.endswith("tbl"):
                tbl = DocxTable(child, doc)
                tbl_text = get_table_text(tbl)
                current_page_text.append(tbl_text)

        if current_page_text:
            pages.append("\n".join(current_page_text))

        if not pages:
            pages = [""]
        return pages

    def get_page_count(self, docx_path: str) -> int:
        """
        Returns the simulated/detected number of pages in the DOCX file.
        """
        pages = self._parse_pages(docx_path)
        return len(pages)

    def process_file(
        self,
        file_path: str,
        session: ExtractionSession | None = None,
        pages_per_unit: int = 1,
    ) -> Generator[tuple[int, int, str], None, None]:
        """
        Processes the DOCX file, yielding (unit_index, total_units, unit_text).
        """
        from pyingestion.extraction_session import NoOpExtractionSession

        session = session or NoOpExtractionSession()

        pages = self._parse_pages(file_path)
        total_pages = len(pages)
        session.total_pages += total_pages

        total_units = (total_pages + pages_per_unit - 1) // pages_per_unit
        unit_pages = []
        unit_index = 1

        for page_text in pages:
            if session.is_cancelled:
                break

            unit_pages.append(page_text)

            if len(unit_pages) == pages_per_unit:
                yield unit_index, total_units, "\n".join(unit_pages)
                unit_pages = []
                unit_index += 1

        if unit_pages and not session.is_cancelled:
            yield unit_index, total_units, "\n".join(unit_pages)


class OcrParser(InputStream):
    """
    OCR parser using pytesseract for text extraction from images and PDFs.
    """

    def accepts(self, file_path: str) -> bool:
        import os

        ext = os.path.splitext(file_path)[1].lower()
        return ext in (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")

    def _check_tesseract(self):
        import shutil

        if not shutil.which("tesseract"):
            raise RuntimeError(
                "Tesseract OCR is not installed or not in system PATH. "
                "Please install tesseract-ocr to use the OCR parser."
            )

    def _check_poppler(self):
        import shutil

        if not shutil.which("pdftoppm") or not shutil.which("pdfinfo"):
            raise RuntimeError(
                "Poppler (pdftoppm/pdfinfo) is not installed or not in system PATH. "
                "Please install poppler-utils to parse PDF files using the OCR parser."
            )

    def get_page_count(self, file_path: str) -> int:
        """
        Returns the number of pages in the PDF file, or 1 for images.
        """
        if file_path.lower().endswith(".pdf"):
            self._check_poppler()
            import pdf2image

            try:
                info = pdf2image.pdfinfo_from_path(file_path)
                return info["Pages"]
            except Exception as e:
                raise RuntimeError(f"Error reading PDF info: {e}")
        return 1

    def process_file(
        self,
        file_path: str,
        session: ExtractionSession | None = None,
        pages_per_unit: int = 1,
    ) -> Generator[tuple[int, int, str], None, None]:
        """
        Processes the image or PDF file page-by-page, running OCR and yielding
        (unit_index, total_units, unit_text).
        """
        from pyingestion.extraction_session import NoOpExtractionSession

        session = session or NoOpExtractionSession()
        self._check_tesseract()

        is_pdf = file_path.lower().endswith(".pdf")
        if is_pdf:
            self._check_poppler()
            import pdf2image
            import pytesseract

            total_pages = self.get_page_count(file_path)
            session.total_pages += total_pages

            total_units = (total_pages + pages_per_unit - 1) // pages_per_unit
            unit_pages = []
            unit_index = 1

            for page_num in range(1, total_pages + 1):
                if session.is_cancelled:
                    break

                try:
                    # Convert single page to PIL image to save memory (lazy extraction)
                    images = pdf2image.convert_from_path(
                        file_path,
                        first_page=page_num,
                        last_page=page_num,
                        dpi=150,
                    )
                    if not images:
                        raise ValueError(f"Failed to convert page {page_num}")
                    page_text = pytesseract.image_to_string(images[0])
                except Exception as e:
                    page_text = ""
                    session.observer.on_error(
                        f"Error running OCR on PDF page {page_num}: {e}"
                    )

                unit_pages.append(page_text)

                if len(unit_pages) == pages_per_unit:
                    yield unit_index, total_units, "\n".join(unit_pages)
                    unit_pages = []
                    unit_index += 1

            if unit_pages and not session.is_cancelled:
                yield unit_index, total_units, "\n".join(unit_pages)

        else:
            # It's a single image file
            import pytesseract
            from PIL import Image

            session.total_pages += 1
            if not session.is_cancelled:
                try:
                    with Image.open(file_path) as img:
                        text = pytesseract.image_to_string(img)
                    yield 1, 1, text
                except Exception as e:
                    session.observer.on_error(f"Error running OCR on image file: {e}")
                    yield 1, 1, ""
