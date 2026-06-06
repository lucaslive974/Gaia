import re
import unicodedata
from abc import ABC, abstractmethod
from typing import Generator

from gaia.extractor import BasePdfExtractor, NativePdfExtractor
from gaia.extraction_session import ExtractionSession


class OcrParser(ABC):
    @abstractmethod
    def process_file(
        self,
        file_path: str,
        session: ExtractionSession | None = None,
        pages_per_unit: int = 1,
    ) -> Generator[tuple[int, int, str], None, None]:
        pass


class DefaultOcrParser(OcrParser):
    def __init__(
        self,
        extractor: BasePdfExtractor | None = None,
    ):
        self._extractor = extractor or NativePdfExtractor()

    def process_file(
        self,
        file_path: str,
        session: ExtractionSession | None = None,
        pages_per_unit: int = 1,
    ) -> Generator[tuple[int, int, str], None, None]:
        from gaia.extraction_session import NoOpExtractionSession
        session = session or NoOpExtractionSession()

        total_pages = self._extractor.get_page_count(file_path)
        session.total_pages += total_pages

        raw_pages = list(self._extractor.extract_pages(file_path))

        units = []
        for i in range(0, len(raw_pages), pages_per_unit):
            unit_chunk = raw_pages[i : i + pages_per_unit]
            unit_text = "\n".join(unit_chunk)
            units.append(unit_text)

        total_units = len(units)

        for unit_index, unit_text in enumerate(units, start=1):
            if session.is_cancelled:
                break
            yield unit_index, total_units, unit_text
