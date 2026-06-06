import re
import os
import unicodedata
from abc import ABC, abstractmethod
from typing import Generator

from core.extractor import BasePdfExtractor, NativePdfExtractor
from core.regex_engine import RegexEngine, NativeRegexEngine
from core.extraction_session import ExtractionSession


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

        from config import settings

        self._regex_engine = regex_engine or NativeRegexEngine(settings.REGEX_FILE)

    def process_file(
        self,
        file_path: str,
        session: ExtractionSession,
    ) -> Generator[dict[str, str], None, None]:
        from config import settings

        total_pages = self._extractor.get_page_count(file_path)
        session.total_pages += total_pages

        pages_per_unit = getattr(settings, "PAGES_PER_UNIT", 1)

        raw_pages = list(self._extractor.extract_pages(file_path))

        # Chunk the pages list into units of pages_per_unit size
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
                f.write(f"FALHA NA EXTRAÇÃO - Página {page_number}\n")
                f.write(f"Erro: {error_msg}\n")
                if extracted_data:
                    f.write(f"Campos extraídos: {extracted_data}\n")
                f.write(f"{'-' * 80}\n")
                f.write(page_text)
                f.write(f"\n{'=' * 80}\n")
        except Exception:
            pass

    def _parse_page(self, page_text: str) -> dict[str, str]:
        # Aplica o seu pré-processamento normal
        text_pos_processed = _pos_processing_text(page_text)

        try:
            resultados = self._regex_engine.parse(text_pos_processed)
        except ValueError as e:
            # If parsing fails due to required fields missing, get partial matches for logging
            partial_results, _ = self._regex_engine.parse_test(text_pos_processed)
            e.extracted_data = partial_results
            raise e

        return resultados


def _pos_processing_text(text: str) -> str:
    text = re.sub(r"[-—|°º]", " ", text)
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")
