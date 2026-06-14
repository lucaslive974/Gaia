from abc import ABC, abstractmethod
from enum import Enum
from typing import Generator
from pyingestion.extraction_session import ExtractionSession


class Parser(ABC):
    """
    Abstract Base Class representing a document/file parser.
    Its responsibility is to identify supported files and extract raw text.
    """

    @abstractmethod
    def accepts(self, file_path: str) -> bool:
        """
        Determines if the parser can handle/process the given file path.
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
        Processes the file, extracting raw text and yielding
        (unit_index, total_units, unit_text).
        """
        pass


class ParserType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    OCR = "ocr"


class ParserFactory:
    @staticmethod
    def _create_pdf_parser() -> Parser:
        from pyingestion.parsers import PdfParser

        return PdfParser()

    @staticmethod
    def _create_docx_parser() -> Parser:
        from pyingestion.parsers import DocxParser

        return DocxParser()

    @staticmethod
    def _create_ocr_parser() -> Parser:
        from pyingestion.parsers import OcrParser

        return OcrParser()

    _CREATORS = {
        "pdf": _create_pdf_parser,
        "docx": _create_docx_parser,
        "ocr": _create_ocr_parser,
    }

    @staticmethod
    def create(parser_type: str | ParserType) -> Parser:
        """
        Lazily creates and returns a Parser instance corresponding to the type.
        """
        pt = parser_type.value if isinstance(parser_type, ParserType) else parser_type
        creator = ParserFactory._CREATORS.get(pt)
        if not creator:
            raise ValueError(f"Unknown parser type: {pt}")
        return creator()
