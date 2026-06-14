from abc import ABC, abstractmethod
from enum import Enum
from typing import Generator
from pyingestion.extraction_session import ExtractionSession


class InputStream(ABC):
    """
    Abstract Base Class representing an input stream (formerly Parser).
    Its responsibility is to identify supported files/sources and extract raw text.
    """

    @abstractmethod
    def accepts(self, file_path: str) -> bool:
        """
        Determines if the input stream can handle/process the given file path.
        """
        pass

    @abstractmethod
    def process_file(
        self,
        file_path: str,
        session: ExtractionSession | None = None,
        pages_per_unit: int = 1,
    ) -> Generator[tuple[int, int, str], None, None]:
        """
        Processes the file/source, extracting raw text and yielding
        (unit_index, total_units, unit_text).
        """
        pass


class InputStreamType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    OCR = "ocr"


class InputStreamFactory:
    @staticmethod
    def _create_pdf_parser() -> InputStream:
        from pyingestion.parsers import PdfParser

        return PdfParser()

    @staticmethod
    def _create_docx_parser() -> InputStream:
        from pyingestion.parsers import DocxParser

        return DocxParser()

    @staticmethod
    def _create_ocr_parser() -> InputStream:
        from pyingestion.parsers import OcrParser

        return OcrParser()

    _CREATORS = {
        "pdf": _create_pdf_parser,
        "docx": _create_docx_parser,
        "ocr": _create_ocr_parser,
    }

    @staticmethod
    def create(parser_type: str | InputStreamType) -> InputStream:
        """
        Lazily creates and returns an InputStream instance corresponding to the type.
        """
        pt = parser_type.value if isinstance(parser_type, InputStreamType) else parser_type
        creator = InputStreamFactory._CREATORS.get(pt)
        if not creator:
            raise ValueError(f"Unknown parser type: {pt}")
        return creator()
