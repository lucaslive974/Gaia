import re
import os
import unicodedata
from abc import ABC, abstractmethod
from typing import Generator

from core.extractor import BasePdfExtractor, NativePdfExtractor
from core.observer import ExtractionObserver
from core.regex_engine import RegexEngine, NativeRegexEngine


class OcrParser(ABC):
    @abstractmethod
    def process_file(
        self,
        file_path: str,
        observer: ExtractionObserver | None = None,
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

        self.successful_pages = 0
        self.failed_pages = 0
        self.total_pages = 0

    def process_file(
        self,
        file_path: str,
        observer: ExtractionObserver | None = None,
    ) -> Generator[dict[str, str], None, None]:
        total_pages = self._extractor.get_page_count(file_path)
        self.total_pages += total_pages

        page_generator = self._extractor.extract_pages(file_path)
        for page_index, page_text in enumerate(page_generator, start=1):
            if observer and getattr(observer, "is_cancelled", False):
                break

            if observer:
                observer.on_page_start(page_index, total_pages)

            try:
                page_dict = self._parse_page(page_text)
                success = True
            except ValueError as e:
                extracted_data = getattr(e, "extracted_data", None)
                self._log_failed_page(page_text, page_index, str(e), extracted_data)
                success = False

            if success:
                self.successful_pages += 1
                yield page_dict
            else:
                self.failed_pages += 1

            if observer:
                observer.on_page_processed(
                    success,
                    self.successful_pages,
                    self.failed_pages,
                    page_index,
                    total_pages,
                )

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
