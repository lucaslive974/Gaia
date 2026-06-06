import os
import time
from config.settings import Settings
from core.extractor import NativePdfExtractor
from core.ocr_parser import DefaultOcrParser
from core.csv_writer import DefaultCsvWriter
from core.observer import ExtractionObserver


class AppController:
    """
    Controller class responsible for orchestrating the CLI execution logic,
    directory validations, PDF discovery (recursive or non-recursive),
    parsing progress, CSV persistence, and execution resumption.
    """

    def __init__(self, observer: ExtractionObserver | None = None):
        self.observer = observer

    def run(self, settings: Settings) -> bool:
        # 1. Validations
        if not os.path.exists(settings.BASE_PATH):
            if self.observer:
                self.observer.on_error(
                    f"O diretório de entrada '{settings.BASE_PATH}' não existe."
                )
            return False

        if not os.path.isdir(settings.BASE_PATH):
            if self.observer:
                self.observer.on_error(
                    f"O caminho de entrada '{settings.BASE_PATH}' não é um diretório."
                )
            return False

        # 2. Create destination output CSV directory
        output_dir = os.path.dirname(settings.OUTPUT_CSV)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 3. Clean up previous gaia_errors.log if not in resume mode
        log_path = os.path.join(os.getcwd(), "gaia_errors.log")
        if not settings.RESUME and os.path.exists(log_path):
            try:
                os.remove(log_path)
            except Exception:
                pass

        # 4. Find all PDF files under settings.BASE_PATH
        files = []
        if settings.RECURSIVE:
            for root, _, filenames in os.walk(settings.BASE_PATH):
                for f in filenames:
                    if f.lower().endswith(".pdf"):
                        # Save relative path to maintain directory structure in resume state
                        rel_path = os.path.relpath(
                            os.path.join(root, f), settings.BASE_PATH
                        )
                        files.append(rel_path)
        else:
            try:
                for f in os.listdir(settings.BASE_PATH):
                    if f.lower().endswith(".pdf"):
                        files.append(f)
            except Exception as e:
                if self.observer:
                    self.observer.on_error(f"Erro ao listar o diretório: {e}")
                return False

        files.sort()
        total_original_files = len(files)

        # 5. Instantiate parser tools
        extractor = NativePdfExtractor()
        csv_writer = DefaultCsvWriter(path_output=settings.OUTPUT_CSV)
        ocr_parser = DefaultOcrParser(extractor=extractor)

        # 6. Load resume state
        processed_files = set()
        ocr_parser.successful_pages = 0
        ocr_parser.failed_pages = 0
        ocr_parser.total_pages = 0

        loaded_state = settings.load_resume_state(settings.BASE_PATH)
        if loaded_state:
            processed_files = set(loaded_state.get("processed_files", []))
            ocr_parser.successful_pages = loaded_state.get(
                "successful_pages", 0
            )
            ocr_parser.failed_pages = loaded_state.get("failed_pages", 0)
            ocr_parser.total_pages = loaded_state.get("total_pages", 0)

        # Filter out already processed files
        remaining_files = [f for f in files if f not in processed_files]
        total_files = len(remaining_files)

        if total_files == 0:
            if self.observer:
                self.observer.on_start(total_original_files)
                self.observer.on_complete(
                    ocr_parser.successful_pages, ocr_parser.total_pages
                )
            return True

        if self.observer:
            self.observer.on_start(total_original_files)

        # Time estimation counters
        estimative_acc = 1200
        estimative_cnt = 1

        for file_index, rel_file_path in enumerate(
            remaining_files, start=len(processed_files) + 1
        ):
            if self.observer and getattr(self.observer, "is_cancelled", False):
                break

            start_time = time.perf_counter()
            full_file_path = os.path.join(settings.BASE_PATH, rel_file_path)

            # Calculate estimation based on remaining files
            _estimative = round(estimative_acc / estimative_cnt)
            remaining_count = total_files - (
                file_index - len(processed_files) - 1
            )
            est_hours = round((remaining_count * _estimative) / 3600.0, 2)

            if self.observer:
                self.observer.on_file_start(
                    file_index, full_file_path, est_hours
                )

            try:
                # AppController executes parser and orchestrates CsvWriter to persist page-by-page
                for page_dict in ocr_parser.process_file(
                    full_file_path, self.observer
                ):
                    csv_writer.write(page_dict)
            except Exception as e:
                if self.observer:
                    self.observer.on_error(
                        f"Erro no arquivo {rel_file_path}: {e}"
                    )
                continue

            # File processed successfully, update resume state
            processed_files.add(rel_file_path)
            settings.save_resume_state(
                settings.BASE_PATH,
                list(processed_files),
                ocr_parser.successful_pages,
                ocr_parser.failed_pages,
                ocr_parser.total_pages,
            )

            if self.observer:
                progress_percent = (file_index / total_original_files) * 100
                self.observer.on_file_complete(file_index, progress_percent)

            estimative_acc += time.perf_counter() - start_time
            estimative_cnt += 1

        # Delete resume state if finished successfully and not cancelled
        if not (self.observer and getattr(self.observer, "is_cancelled", False)):
            settings.clear_resume_state(settings.BASE_PATH)

        if self.observer:
            self.observer.on_complete(
                ocr_parser.successful_pages, ocr_parser.total_pages
            )

        return True
