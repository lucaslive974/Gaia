from abc import ABC, abstractmethod
from enum import Enum
from typing import Generator
from gaia.extraction_session import ExtractionSession


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


class ParserFactory:
    @staticmethod
    def _create_pdf_parser() -> Parser:
        from gaia.pdf_parser import PdfParser
        return PdfParser()

    _CREATORS = {
        "pdf": _create_pdf_parser,
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
