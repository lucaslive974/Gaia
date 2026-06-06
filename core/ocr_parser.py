import re
import time
import os
import unicodedata
from os import path, listdir
from abc import ABC, abstractmethod

from core.extractor import BasePdfExtractor, NativePdfExtractor
from core.csv_writer import CsvWriter, DefaultCsvWriter
from core.observer import ExtractionObserver
from core.regex_engine import RegexEngine, NativeRegexEngine


class OcrParser(ABC):
    @abstractmethod
    def process(
        self,
        dir_path: str,
        observer: ExtractionObserver | None = None,
        resume: bool = False,
    ):
        pass


class DefaultOcrParser(OcrParser):
    def __init__(
        self,
        extractor: BasePdfExtractor | None = None,
        csv_writer: CsvWriter | None = None,
        regex_engine: RegexEngine | None = None,
    ):
        self._extractor = extractor or NativePdfExtractor()
        self._csv_writer = csv_writer or DefaultCsvWriter()

        from config import settings

        self._regex_engine = regex_engine or NativeRegexEngine(settings.REGEX_FILE)

        self._estimative_acc = 1200
        self._estimative_cnt = 1

    def process(
        self,
        dir_path: str,
        observer: ExtractionObserver | None = None,
        resume: bool = False,
    ):
        self._verify_path(dir_path)
        self._total_pages = 0
        self._successful_pages = 0
        self._failed_pages = 0

        try:
            files = [f for f in listdir(dir_path) if f.lower().endswith(".pdf")]
        except Exception as e:
            if observer:
                observer.on_error(f"Erro ao listar o diretório: {e}")
            raise e

        # Resolve output path for state tracking
        from config import settings

        processed_files = set()

        # We automatically resume if the file exists in either location, regardless of 'resume' flag
        loaded_state = settings.load_resume_state(dir_path)

        if loaded_state:
            processed_files = set(loaded_state.get("processed_files", []))
            self._successful_pages = loaded_state.get("successful_pages", 0)
            self._failed_pages = loaded_state.get("failed_pages", 0)
            self._total_pages = loaded_state.get("total_pages", 0)

        # Filter out already processed files
        remaining_files = [f for f in files if f not in processed_files]
        total_files = len(remaining_files)
        total_original_files = len(files)

        if total_files == 0:
            if observer:
                observer.on_start(total_original_files)
                observer.on_complete(self._successful_pages, self._total_pages)
            return

        if observer:
            observer.on_start(total_original_files)

        for file_index, file in enumerate(
            remaining_files, start=len(processed_files) + 1
        ):
            if observer and getattr(observer, "is_cancelled", False):
                break

            start_time = time.perf_counter()
            file_path = path.join(dir_path, file)

            # Calculate estimation based on remaining files
            _estimative = round(self._estimative_acc / self._estimative_cnt)
            remaining_count = total_files - (file_index - len(processed_files) - 1)
            est_hours = round((remaining_count * _estimative) / 3600.0, 2)

            if observer:
                observer.on_file_start(file_index, file_path, est_hours)

            try:
                self._process_file(file_path, observer)
            except Exception as e:
                if observer:
                    observer.on_error(f"Erro no arquivo {file}: {e}")
                continue

            # File processed successfully, update resume state in both files via settings
            processed_files.add(file)
            settings.save_resume_state(
                dir_path,
                list(processed_files),
                self._successful_pages,
                self._failed_pages,
                self._total_pages,
            )

            if observer:
                progress_percent = (file_index / total_original_files) * 100
                observer.on_file_complete(file_index, progress_percent)

            self._estimative_acc += time.perf_counter() - start_time
            self._estimative_cnt += 1

        # Delete resume state if finished successfully and not cancelled
        if not (observer and getattr(observer, "is_cancelled", False)):
            settings.clear_resume_state(dir_path)

        if observer:
            observer.on_complete(self._successful_pages, self._total_pages)

    def _process_file(self, file_path: str, observer: ExtractionObserver | None):
        total_pages = self._extractor.get_page_count(file_path)
        self._total_pages += total_pages

        page_generator = self._extractor.extract_pages(file_path)
        for page_index, page_text in enumerate(page_generator, start=1):
            if observer and getattr(observer, "is_cancelled", False):
                break

            if observer:
                observer.on_page_start(page_index, total_pages)

            success = self._process_page(page_text, page_index)
            if success:
                self._successful_pages += 1
            else:
                self._failed_pages += 1

            if observer:
                observer.on_page_processed(
                    success,
                    self._successful_pages,
                    self._failed_pages,
                    page_index,
                    total_pages,
                )

    def _process_page(self, page_text: str, page_number: int) -> bool:
        try:
            page_dict = self._parse_page(page_text)
            self._csv_writer.write(page_dict)
            return True
        except ValueError as e:
            extracted_data = getattr(e, "extracted_data", None)
            self._log_failed_page(page_text, page_number, str(e), extracted_data)
            return False

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

    _KEY_MAP = {
        "data_emissao": "DAT_EMISS",
        "data_vencimento": "DAT_VENC",
        "n_infracao": "AI",
        "concessionaria": "CONCESSIONARIA",
        "linha": "LINHA",
        "veiculo": "VEICULO",
        "placa": "PLACA",
        "data_ocorrencia": "DAT_OCORRENCIA",
        "hora_ocorrencia": "HORA_OCORRENCIA",
        "local": "LOCAL",
        "descricao": "DESCRICAO",
        "valor": "VALOR",
    }

    def _parse_page(self, page_text: str) -> dict[str, str]:
        # Aplica o seu pré-processamento normal
        text_pos_processed = _pos_processing_text(page_text)

        try:
            resultados = self._regex_engine.parse(text_pos_processed)
        except ValueError as e:
            # If parsing fails due to required fields missing, get partial matches for logging
            partial_results, _ = self._regex_engine.parse_test(text_pos_processed)
            mapped_partial = {
                self._KEY_MAP.get(k, k): v for k, v in partial_results.items()
            }
            e.extracted_data = mapped_partial
            raise e

        # Map internal keys to final CSV keys
        mapped_resultados = {
            self._KEY_MAP.get(k, k): v for k, v in resultados.items()
        }
        return mapped_resultados

    def _verify_path(self, dir_path: str):
        if not path.exists(dir_path):
            raise FileNotFoundError("Diretório especificado não existe")


def _pos_processing_text(text: str) -> str:
    text = re.sub(r"[-—|°º]", " ", text)
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")
