import os
from pydocstructurer.options import Options
from pydocstructurer import (
    OutputStream,
    DefaultOutputStream,
    DefaultExtractionObserver,
    ExtractionObserver,
    ExtractionSession,
    NativeRegexEngine,
)
from pydocstructurer.parser import Parser, ParserFactory
from pydocstructurer.i18n import _


class PyDocStructurer:
    """
    Main global class (Codename: Gaia) responsible for orchestrating the execution logic,
    directory validations, file discovery, parsing progress, output persistence,
    and execution resumption.
    """

    def __init__(
        self,
        options: Options,
        observer: ExtractionObserver | None = None,
        output_stream: OutputStream | None = None,
        regex_engine: NativeRegexEngine | None = None,
        parser: Parser | None = None,
    ):
        self.options = options
        self.observer = observer or DefaultExtractionObserver()
        self.output_stream = output_stream or DefaultOutputStream()
        self.regex_engine = regex_engine or NativeRegexEngine.from_file(
            options.REGEX_FILE
        )
        self.parser = parser or ParserFactory.create(options.PARSER_TYPE)

    def run(self, options: Options | None = None) -> bool:
        if options is not None:
            self.options = options

        # 1. Validations
        if not self._validate_paths():
            return False

        # 2. Preparation
        self._prepare_environment()

        # 3. Find files
        files = self._find_files()
        if files is None:
            return False

        total_original_files = len(files)

        # 4. Initialize session
        session = ExtractionSession.restore_or_create(self.options, self.observer)

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
        if not os.path.exists(self.options.BASE_PATH):
            self.observer.on_error(
                _("err_dir_not_exist", base_path=self.options.BASE_PATH)
            )
            return False

        if not os.path.isdir(self.options.BASE_PATH) and not os.path.isfile(self.options.BASE_PATH):
            self.observer.on_error(
                _("err_not_a_dir", base_path=self.options.BASE_PATH)
            )
            return False
        return True

    def _prepare_environment(self) -> None:
        output_dir = os.path.dirname(self.options.OUTPUT_CSV)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        log_path = os.path.join(os.getcwd(), "gaia_errors.log")
        if not self.options.RESUME and os.path.exists(log_path):
            try:
                os.remove(log_path)
            except Exception:
                pass

    def _find_files(self) -> list[str] | None:
        if os.path.isfile(self.options.BASE_PATH):
            if self.parser.accepts(self.options.BASE_PATH):
                return [os.path.basename(self.options.BASE_PATH)]
            return []

        files = []
        if self.options.RECURSIVE:
            for root, dirs, filenames in os.walk(self.options.BASE_PATH):
                for f in filenames:
                    full_path = os.path.join(root, f)
                    if self.parser.accepts(full_path):
                        rel_path = os.path.relpath(
                            full_path, self.options.BASE_PATH
                        )
                        files.append(rel_path)
        else:
            try:
                for f in os.listdir(self.options.BASE_PATH):
                    full_path = os.path.join(self.options.BASE_PATH, f)
                    if self.parser.accepts(full_path):
                        files.append(f)
            except Exception as e:
                self.observer.on_error(_("err_list_dir", error=e))
                return None

        files.sort()
        return files

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
        if os.path.isdir(self.options.BASE_PATH):
            full_file_path = os.path.join(self.options.BASE_PATH, rel_file_path)
        else:
            full_file_path = self.options.BASE_PATH
        session.start_file(file_index, full_file_path)

        try:
            for unit_index, total_units, unit_text in self.parser.process_file(
                full_file_path, session, pages_per_unit=self.options.PAGES_PER_UNIT
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
        session.save_state()
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
            session.clear_state()
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
