import os
from collections.abc import Generator

from pypdf import PdfReader

from pyingestion.extraction_session import ExtractionSession
from pyingestion.input_stream import FileInputStream


class PdfInputStream(FileInputStream):
    """
    PDF input stream using layout-based text extraction from pypdf.
    """

    def __init__(self, pages_per_unit: int = 1, recursive: bool = False):
        self.pages_per_unit = pages_per_unit
        self.recursive = recursive
        self.current_unit_index = 0
        self.total_units = 0

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

    def read(
        self, source: str, session: ExtractionSession | None = None
    ) -> Generator[str, None, None]:
        files = self._find_files(source)
        if session:
            session.start(len(files))
            processed_files_set = set(session.processed_files)
        else:
            processed_files_set = set()

        for idx, rel_file_path in enumerate(files, start=1):
            if rel_file_path in processed_files_set:
                continue

            if os.path.isdir(source):
                full_file_path = os.path.join(source, rel_file_path)
            else:
                full_file_path = source

            if session:
                if session.is_cancelled:
                    break
                session.start_file(idx, full_file_path)

            try:
                reader = PdfReader(full_file_path)
                total_pages = len(reader.pages)
                if session:
                    session.total_pages += total_pages

                total_units = (
                    total_pages + self.pages_per_unit - 1
                ) // self.pages_per_unit
                self.total_units = total_units

                unit_pages = []
                unit_index = 1

                for page_num in range(1, total_pages + 1):
                    if session and session.is_cancelled:
                        break

                    self.current_unit_index = unit_index

                    page_text = self._extract_single_page(reader, page_num)
                    unit_pages.append(page_text)

                    if len(unit_pages) == self.pages_per_unit:
                        yield "\n".join(unit_pages)
                        unit_pages = []
                        unit_index += 1

                if unit_pages and not (session and session.is_cancelled):
                    self.current_unit_index = unit_index
                    yield "\n".join(unit_pages)

            except Exception as e:
                if session:
                    session.error(f"Error in file {rel_file_path}: {e}")
                else:
                    raise e
                continue

            if session:
                session.processed_files.append(rel_file_path)
                session.save(source)
                session.complete_file(idx)

        if session and not session.is_cancelled:
            session.clear(source)


class DocxInputStream(FileInputStream):
    """
    DOCX input stream using python-docx to extract text.
    """

    def __init__(self, pages_per_unit: int = 1, recursive: bool = False):
        self.pages_per_unit = pages_per_unit
        self.recursive = recursive
        self.current_unit_index = 0
        self.total_units = 0

    def accepts(self, file_path: str) -> bool:
        return file_path.lower().endswith(".docx")

    def _parse_pages(self, docx_path: str) -> list[str]:
        import docx
        from docx.table import Table as DocxTable
        from docx.text.paragraph import Paragraph

        doc = docx.Document(docx_path)
        pages = []
        current_page_text = []

        def has_page_break(p: Paragraph) -> bool:
            if p.paragraph_format.page_break_before:
                return True
            p_xml = p._element.xml  # pyright: ignore[reportPrivateUsage]
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

    def read(
        self, source: str, session: ExtractionSession | None = None
    ) -> Generator[str, None, None]:
        files = self._find_files(source)
        if session:
            session.start(len(files))
            processed_files_set = set(session.processed_files)
        else:
            processed_files_set = set()

        for idx, rel_file_path in enumerate(files, start=1):
            if rel_file_path in processed_files_set:
                continue

            if os.path.isdir(source):
                full_file_path = os.path.join(source, rel_file_path)
            else:
                full_file_path = source

            if session:
                if session.is_cancelled:
                    break
                session.start_file(idx, full_file_path)

            try:
                pages = self._parse_pages(full_file_path)
                total_pages = len(pages)
                if session:
                    session.total_pages += total_pages

                total_units = (
                    total_pages + self.pages_per_unit - 1
                ) // self.pages_per_unit
                self.total_units = total_units

                unit_pages = []
                unit_index = 1

                for page_text in pages:
                    if session and session.is_cancelled:
                        break

                    self.current_unit_index = unit_index
                    unit_pages.append(page_text)

                    if len(unit_pages) == self.pages_per_unit:
                        yield "\n".join(unit_pages)
                        unit_pages = []
                        unit_index += 1

                if unit_pages and not (session and session.is_cancelled):
                    self.current_unit_index = unit_index
                    yield "\n".join(unit_pages)

            except Exception as e:
                if session:
                    session.error(f"Error in file {rel_file_path}: {e}")
                else:
                    raise e
                continue

            if session:
                session.processed_files.append(rel_file_path)
                session.save(source)
                session.complete_file(idx)

        if session and not session.is_cancelled:
            session.clear(source)


class OcrInputStream(FileInputStream):
    """
    OCR input stream using pytesseract for text extraction from images and PDFs.
    """

    def __init__(self, pages_per_unit: int = 1, recursive: bool = False):
        self.pages_per_unit = pages_per_unit
        self.recursive = recursive
        self.current_unit_index = 0
        self.total_units = 0

    def accepts(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")

    def _check_tesseract(self):
        import shutil

        if not shutil.which("tesseract"):
            raise RuntimeError(
                "Tesseract OCR is not installed or not in system PATH. "
                + "Please install tesseract-ocr to use the OCR parser."
            )

    def _check_poppler(self):
        import shutil

        if not shutil.which("pdftoppm") or not shutil.which("pdfinfo"):
            raise RuntimeError(
                "Poppler (pdftoppm/pdfinfo) is not installed or not in system PATH. "
                + "Please install poppler-utils to parse PDF files using the OCR parser."
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

    def read(
        self, source: str, session: ExtractionSession | None = None
    ) -> Generator[str, None, None]:
        files = self._find_files(source)
        if session:
            session.start(len(files))
            processed_files_set = set(session.processed_files)
        else:
            processed_files_set = set()

        for idx, rel_file_path in enumerate(files, start=1):
            if rel_file_path in processed_files_set:
                continue

            if os.path.isdir(source):
                full_file_path = os.path.join(source, rel_file_path)
            else:
                full_file_path = source

            if session:
                if session.is_cancelled:
                    break
                session.start_file(idx, full_file_path)

            try:
                is_pdf = full_file_path.lower().endswith(".pdf")
                if is_pdf:
                    self._check_poppler()
                    self._check_tesseract()
                    import pdf2image
                    import pytesseract  # pyright: ignore[reportMissingTypeStubs]

                    total_pages = self.get_page_count(full_file_path)
                    if session:
                        session.total_pages += total_pages

                    total_units = (
                        total_pages + self.pages_per_unit - 1
                    ) // self.pages_per_unit
                    self.total_units = total_units

                    unit_pages = []
                    unit_index = 1

                    for page_num in range(1, total_pages + 1):
                        if session and session.is_cancelled:
                            break

                        self.current_unit_index = unit_index

                        try:
                            images = pdf2image.convert_from_path(
                                full_file_path,
                                first_page=page_num,
                                last_page=page_num,
                                dpi=150,
                            )
                            if not images:
                                raise ValueError(f"Failed to convert page {page_num}")
                            page_text = pytesseract.image_to_string(images[0])
                        except Exception as e:
                            page_text = ""
                            if session:
                                session.observer.on_error(
                                    f"Error running OCR on PDF page {page_num}: {e}"
                                )
                            else:
                                raise e

                        unit_pages.append(page_text)

                        if len(unit_pages) == self.pages_per_unit:
                            yield "\n".join(unit_pages)
                            unit_pages = []
                            unit_index += 1

                    if unit_pages and not (session and session.is_cancelled):
                        self.current_unit_index = unit_index
                        yield "\n".join(unit_pages)

                else:
                    self._check_tesseract()
                    import pytesseract  # pyright: ignore[reportMissingTypeStubs]
                    from PIL import Image

                    if session:
                        session.total_pages += 1

                    self.total_units = 1
                    self.current_unit_index = 1

                    text = ""
                    try:
                        with Image.open(full_file_path) as img:
                            text = pytesseract.image_to_string(img)
                    except Exception as e:
                        if session:
                            session.observer.on_error(
                                f"Error running OCR on image file: {e}"
                            )
                        else:
                            raise e

                    yield str(text)

            except Exception as e:
                if session:
                    session.error(f"Error in file {rel_file_path}: {e}")
                else:
                    raise e
                continue

            if session:
                session.processed_files.append(rel_file_path)
                session.save(source)
                session.complete_file(idx)

        if session and not session.is_cancelled:
            session.clear(source)


from enum import Enum

from pyingestion.input_stream import InputStream


class InputStreamType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    OCR = "ocr"


class InputStreamFactory:
    @staticmethod
    def _create_pdf_parser(
        pages_per_unit: int = 1, recursive: bool = False
    ) -> InputStream[str, str]:
        from pyingestion.input_streams import PdfInputStream

        return PdfInputStream(pages_per_unit=pages_per_unit, recursive=recursive)

    @staticmethod
    def _create_docx_parser(
        pages_per_unit: int = 1, recursive: bool = False
    ) -> InputStream[str, str]:
        from pyingestion.input_streams import DocxInputStream

        return DocxInputStream(pages_per_unit=pages_per_unit, recursive=recursive)

    @staticmethod
    def _create_ocr_parser(
        pages_per_unit: int = 1, recursive: bool = False
    ) -> InputStream[str, str]:
        from pyingestion.input_streams import OcrInputStream

        return OcrInputStream(pages_per_unit=pages_per_unit, recursive=recursive)

    _CREATORS = {
        "pdf": _create_pdf_parser,
        "docx": _create_docx_parser,
        "ocr": _create_ocr_parser,
    }

    @staticmethod
    def create(
        parser_type: str | InputStreamType,
        pages_per_unit: int = 1,
        recursive: bool = False,
    ) -> InputStream[str, str]:
        """
        Lazily creates and returns an InputStream instance corresponding to the type.
        """
        pt = (
            parser_type.value
            if isinstance(parser_type, InputStreamType)
            else parser_type
        )
        creator = InputStreamFactory._CREATORS.get(pt)
        if not creator:
            raise ValueError(f"Unknown parser type: {pt}")
        return creator(pages_per_unit=pages_per_unit, recursive=recursive)

    @staticmethod
    def from_file_path(
        file_path: str,
        pages_per_unit: int = 1,
        recursive: bool = False,
    ) -> InputStream[str, str]:
        """
        Detects the correct InputStream parser based on the file extension.
        """
        import os

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".docx":
            return InputStreamFactory.create("docx", pages_per_unit, recursive)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            return InputStreamFactory.create("ocr", pages_per_unit, recursive)
        else:
            return InputStreamFactory.create("pdf", pages_per_unit, recursive)
