import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Generator, Any, Generic, TypeVar
from pyingestion.extraction_session import ExtractionSession

T_source = TypeVar("T_source")
T_out = TypeVar("T_out")


class InputStream(Generic[T_source, T_out], ABC):
    """
    Abstract Base Class representing a generic input stream.
    Its responsibility is to read from a source and yield text units.
    """

    @abstractmethod
    def read(
        self, source: T_source, session: ExtractionSession | None = None
    ) -> Generator[T_out, None, None]:
        """
        Reads from the source, updates the session, and yields groups (units) of text.
        """
        pass


class FileInputStream(InputStream[str, str], ABC):
    """
    Abstract Base Class representing a file-system based input stream.
    """

    @abstractmethod
    def accepts(self, file_path: str) -> bool:
        """
        Returns True if the stream supports the file extension, False otherwise.
        """
        pass

    def _find_files(self, source: str) -> list[str]:
        if os.path.isfile(source):
            if self.accepts(source):
                return [os.path.basename(source)]
            return []

        files = []
        if getattr(self, "recursive", False):
            for root, dirs, filenames in os.walk(source):
                for f in filenames:
                    full_path = os.path.join(root, f)
                    if self.accepts(full_path):
                        rel_path = os.path.relpath(full_path, source)
                        files.append(rel_path)
        else:
            try:
                for f in os.listdir(source):
                    full_path = os.path.join(source, f)
                    if self.accepts(full_path):
                        files.append(f)
            except Exception:
                pass

        files.sort()
        return files


class InputStreamType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    OCR = "ocr"


class InputStreamFactory:
    @staticmethod
    def _create_pdf_parser(
        pages_per_unit: int = 1, recursive: bool = False
    ) -> InputStream:
        from pyingestion.input_streams import PdfInputStream

        return PdfInputStream(pages_per_unit=pages_per_unit, recursive=recursive)

    @staticmethod
    def _create_docx_parser(
        pages_per_unit: int = 1, recursive: bool = False
    ) -> InputStream:
        from pyingestion.input_streams import DocxInputStream

        return DocxInputStream(pages_per_unit=pages_per_unit, recursive=recursive)

    @staticmethod
    def _create_ocr_parser(
        pages_per_unit: int = 1, recursive: bool = False
    ) -> InputStream:
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
    ) -> InputStream:
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
