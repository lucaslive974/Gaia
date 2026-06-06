import re
import os
import unicodedata
from abc import ABC, abstractmethod
from typing import Generator

from core.extractor import BasePdfExtractor, NativePdfExtractor
from core.regex_engine import RegexEngine
from core.extraction_session import ExtractionSession
from core.i18n import _


class OcrParser(ABC):
    @abstractmethod
    def process_file(
        self,
        file_path: str,
        session: ExtractionSession,
    ) -> Generator[dict[str, str], None, None]:
        pass


class DefaultOcrParser(OcrParser):
    def __init__(
        self,
        extractor: BasePdfExtractor | None = None,
        regex_engine: RegexEngine | None = None,
    ):
        self._extractor = extractor or NativePdfExtractor()
        if regex_engine is None:
            raise ValueError("regex_engine must be provided")
        self._regex_engine = regex_engine

    def process_file(
        self,
        file_path: str,
        session: ExtractionSession,
        pages_per_unit: int = 1,
    ) -> Generator[dict[str, str], None, None]:
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

            session.start_page(unit_index, total_units)

            try:
                page_dict = self._parse_page(unit_text)
                success = True
            except ValueError as e:
                extracted_data = getattr(e, "extracted_data", None)
                self._log_failed_page(unit_text, unit_index, str(e), extracted_data)
                success = False

            if success:
                session.process_page_result(True, unit_index, total_units)
                yield page_dict
            else:
                session.process_page_result(False, unit_index, total_units)

    def _log_failed_page(
        self,
        page_text: str,
        page_number: int,
        error_msg: str,
        extracted_data: dict[str, str] | None = None,
    ):
        log_path = os.path.join(os.getcwd(), "gaia_errors.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 80}\n")
                f.write(_("log_fail_extraction", page_number=page_number) + "\n")
                f.write(_("log_error", error=error_msg) + "\n")
                if extracted_data:
                    f.write(_("log_extracted_fields", fields=extracted_data) + "\n")
                f.write(f"{'-' * 80}\n")
                f.write(page_text)
                f.write(f"\n{'=' * 80}\n")
        except Exception:
            pass

    def _parse_page(self, page_text: str) -> dict[str, str]:
        text_pos_processed = _pos_processing_text(page_text)

        try:
            resultados = self._regex_engine.parse(text_pos_processed)
        except ValueError as e:
            partial_results, _ = self._regex_engine.parse_test(text_pos_processed)
            e.extracted_data = partial_results
            raise e

        return resultados


def _pos_processing_text(text: str) -> str:
    text = re.sub(r"[-—|°º]", " ", text)
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")
