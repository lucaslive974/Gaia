import os
from gaia.config.settings import Settings
from gaia import (
    NativePdfParser,
    PdfParser,
    OutputStream,
    DefaultOutputStream,
    DefaultExtractionObserver,
    ExtractionObserver,
    ExtractionSession,
    NativeRegexEngine,
)
from gaia.i18n import _


class Gaia:
    """
    Main global class responsible for orchestrating the execution logic,
    directory validations, PDF discovery, parsing progress, output persistence,
    and execution resumption.
    """

    def __init__(
        self,
        settings: Settings,
        observer: ExtractionObserver | None = None,
        output_stream: OutputStream | None = None,
        regex_engine: NativeRegexEngine | None = None,
        pdf_parser: PdfParser | None = None,
    ):
        self.settings = settings
        self.observer = observer or DefaultExtractionObserver()
        self.output_stream = output_stream or DefaultOutputStream()
        self.regex_engine = regex_engine or NativeRegexEngine.from_file(
            settings.REGEX_FILE
        )
        self.pdf_parser = pdf_parser or NativePdfParser()

    def run(self, settings: Settings | None = None) -> bool:
        if settings is not None:
            self.settings = settings

        # 1. Validations
        if not self._validate_paths():
            return False

        # 2. Preparation
        self._prepare_environment()

        # 3. Find files
        files = self._find_pdf_files()
        if files is None:
            return False

        total_original_files = len(files)

        # 4. Initialize session
        session = ExtractionSession(self.observer)
        self._load_resume_state(session)

        processed_files_set = set(session.processed_files)
        remaining_files = [f for f in files if f not in processed_files_set]
        total_files = len(remaining_files)

        if total_files == 0:
            session.start(total_original_files)
            session.complete()
            return True

        session.start(total_original_files)

        # 5. Process remaining files
        self._process_remaining_files(session, remaining_files, processed_files_set)

        # 6. Finalize session
        self._finalize_session(session)

        return True

    def _validate_paths(self) -> bool:
        if not os.path.exists(self.settings.BASE_PATH):
            self.observer.on_error(
                _("err_dir_not_exist", base_path=self.settings.BASE_PATH)
            )
            return False

        if not os.path.isdir(self.settings.BASE_PATH):
            self.observer.on_error(
                _("err_not_a_dir", base_path=self.settings.BASE_PATH)
            )
            return False
        return True

    def _prepare_environment(self) -> None:
        output_dir = os.path.dirname(self.settings.OUTPUT_CSV)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        log_path = os.path.join(os.getcwd(), "gaia_errors.log")
        if not self.settings.RESUME and os.path.exists(log_path):
            try:
                os.remove(log_path)
            except Exception:
                pass

    def _find_pdf_files(self) -> list[str] | None:
        files = []
        if self.settings.RECURSIVE:
            for root, dirs, filenames in os.walk(self.settings.BASE_PATH):
                for f in filenames:
                    if f.lower().endswith(".pdf"):
                        rel_path = os.path.relpath(
                            os.path.join(root, f), self.settings.BASE_PATH
                        )
                        files.append(rel_path)
        else:
            try:
                for f in os.listdir(self.settings.BASE_PATH):
                    if f.lower().endswith(".pdf"):
                        files.append(f)
            except Exception as e:
                self.observer.on_error(_("err_list_dir", error=e))
                return None

        files.sort()
        return files

    def _load_resume_state(self, session: ExtractionSession) -> None:
        loaded_state = self.settings.load_resume_state(self.settings.BASE_PATH)
        if loaded_state:
            session.processed_files = loaded_state.get("processed_files", [])
            session.successful_pages = loaded_state.get("successful_pages", 0)
            session.failed_pages = loaded_state.get("failed_pages", 0)
            session.total_pages = loaded_state.get("total_pages", 0)

    def _process_remaining_files(
        self,
        session: ExtractionSession,
        remaining_files: list[str],
        processed_files_set: set[str],
    ) -> None:
        for file_index, rel_file_path in enumerate(
            remaining_files, start=len(processed_files_set) + 1
        ):
            if session.is_cancelled and getattr(self.observer, "is_cancelled", False):
                session.is_cancelled = True
                break

            self._process_single_file(session, file_index, rel_file_path)

    def _process_single_file(
        self, session: ExtractionSession, file_index: int, rel_file_path: str
    ) -> None:
        full_file_path = os.path.join(self.settings.BASE_PATH, rel_file_path)
        session.start_file(file_index, full_file_path)

        try:
            for unit_index, total_units, unit_text in self.pdf_parser.process_file(
                full_file_path, session, pages_per_unit=self.settings.PAGES_PER_UNIT
            ):
                # Verify blank pages
                if not unit_text.strip():
                    continue

                session.start_page(unit_index, total_units)
                self._process_page(unit_text, unit_index, total_units, session)
        except Exception as e:
            session.error(_("err_in_file", file_path=rel_file_path, error=e))
            return

        session.processed_files.append(rel_file_path)
        self.settings.save_resume_state(
            self.settings.BASE_PATH,
            session.processed_files,
            session.successful_pages,
            session.failed_pages,
            session.total_pages,
        )
        session.complete_file(file_index)

    def _process_page(
        self,
        unit_text: str,
        unit_index: int,
        total_units: int,
        session: ExtractionSession,
    ) -> None:
        try:
            page_dict = self.regex_engine.parse(unit_text)
            session.process_page_result(True, unit_index, total_units)
            self.output_stream.write(page_dict)
        except ValueError as e:
            # Get partial results for error logging
            partial_results, _u = self.regex_engine.parse_test(unit_text)
            self._log_failed_page(unit_text, unit_index, str(e), partial_results)
            session.process_page_result(False, unit_index, total_units)

    def _finalize_session(self, session: ExtractionSession) -> None:
        # Delete resume state if finished successfully and not cancelled
        if not session.is_cancelled:
            self.settings.clear_resume_state(self.settings.BASE_PATH)
        session.complete()

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
