import os
from config.settings import Settings
from gaia import (
    NativePdfExtractor,
    DefaultOcrParser,
    DefaultCsvWriter,
    ExtractionObserver,
    ExtractionSession,
    NativeRegexEngine,
)
from gaia.i18n import _


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
                    _("err_dir_not_exist", base_path=settings.BASE_PATH)
                )
            return False

        if not os.path.isdir(settings.BASE_PATH):
            if self.observer:
                self.observer.on_error(
                    _("err_not_a_dir", base_path=settings.BASE_PATH)
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
                    self.observer.on_error(_("err_list_dir", error=e))
                return False

        files.sort()
        total_original_files = len(files)

        # 5. Instantiate session
        session = ExtractionSession(self.observer)

        # 6. Instantiate parser tools
        extractor = NativePdfExtractor()
        csv_writer = DefaultCsvWriter(path_output=settings.OUTPUT_CSV)
        regex_engine = NativeRegexEngine.from_file(settings.REGEX_FILE)
        ocr_parser = DefaultOcrParser(extractor=extractor, regex_engine=regex_engine)

        # 7. Load resume state
        loaded_state = settings.load_resume_state(settings.BASE_PATH)
        if loaded_state:
            session.processed_files = loaded_state.get("processed_files", [])
            session.successful_pages = loaded_state.get("successful_pages", 0)
            session.failed_pages = loaded_state.get("failed_pages", 0)
            session.total_pages = loaded_state.get("total_pages", 0)

        processed_files_set = set(session.processed_files)

        # Filter out already processed files
        remaining_files = [f for f in files if f not in processed_files_set]
        total_files = len(remaining_files)

        if total_files == 0:
            session.start(total_original_files)
            session.complete()
            return True

        session.start(total_original_files)

        for file_index, rel_file_path in enumerate(
            remaining_files, start=len(processed_files_set) + 1
        ):
            if session.is_cancelled or (
                self.observer and getattr(self.observer, "is_cancelled", False)
            ):
                session.is_cancelled = True
                break

            full_file_path = os.path.join(settings.BASE_PATH, rel_file_path)

            session.start_file(file_index, full_file_path)

            try:
                # AppController executes parser and orchestrates CsvWriter to persist page-by-page
                for page_dict in ocr_parser.process_file(
                    full_file_path, session, pages_per_unit=settings.PAGES_PER_UNIT
                ):
                    csv_writer.write(page_dict)
            except Exception as e:
                session.error(_("err_in_file", file_path=rel_file_path, error=e))
                continue

            # File processed successfully, update resume state
            session.processed_files.append(rel_file_path)
            settings.save_resume_state(
                settings.BASE_PATH,
                session.processed_files,
                session.successful_pages,
                session.failed_pages,
                session.total_pages,
            )

            session.complete_file(file_index)

        # Delete resume state if finished successfully and not cancelled
        if not session.is_cancelled:
            settings.clear_resume_state(settings.BASE_PATH)

        session.complete()

        return True
