import time
import json
import os
from pydocstructurer.observer import ExtractionObserver, DefaultExtractionObserver


class ExtractionSession:
    def __init__(self, observer: ExtractionObserver | None = None):
        self.observer = observer or DefaultExtractionObserver()
        self._is_cancelled: bool = False
        self.total_files: int = 0
        self.file_index: int = 0
        self.current_file_path: str = ""
        self.successful_pages: int = 0
        self.failed_pages: int = 0
        self.total_pages: int = 0
        self.processed_files: list[str] = []
        self.input_dir: str | None = None
        self.output_file: str | None = None
        self.regex_file: str | None = None

        self.estimative_acc: float = 1200.0
        self.estimative_cnt: int = 1
        self._file_start_time: float = 0.0

    def start(self, total_files: int):
        self.total_files = total_files
        self.observer.on_start(total_files)

    def start_file(self, file_index: int, file_path: str):
        self.file_index = file_index
        self.current_file_path = file_path
        self._file_start_time = time.perf_counter()

        _estimative = round(self.estimative_acc / self.estimative_cnt)
        remaining_count = self.total_files - self.file_index + 1
        est_hours = round((remaining_count * _estimative) / 3600.0, 2)

        self.observer.on_file_start(file_index, file_path, est_hours)

    def start_page(self, page_index: int, total_pages: int):
        self.observer.on_page_start(page_index, total_pages)

    def process_page_result(self, success: bool, page_index: int, total_pages: int):
        if success:
            self.successful_pages += 1
        else:
            self.failed_pages += 1

        self.observer.on_page_processed(
            success,
            self.successful_pages,
            self.failed_pages,
            page_index,
            total_pages,
        )

    def complete_file(self, file_index: int):
        elapsed = time.perf_counter() - self._file_start_time
        self.estimative_acc += elapsed
        self.estimative_cnt += 1

        progress_percent = (file_index / self.total_files) * 100
        self.observer.on_file_complete(file_index, progress_percent)

    def complete(self):
        self.observer.on_complete(self.successful_pages, self.total_pages)

    def error(self, error_message: str):
        self.observer.on_error(error_message)

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled or getattr(self.observer, "is_cancelled", False)

    @is_cancelled.setter
    def is_cancelled(self, value: bool):
        self._is_cancelled = value

    @classmethod
    def get_state_file_paths(cls, input_dir: str | None = None) -> list[str]:
        paths = [os.path.join(os.getcwd(), ".gaia_resume.json")]
        if input_dir:
            paths.append(os.path.join(input_dir, ".gaia_resume.json"))
        return list(set(paths))

    @classmethod
    def load_state(cls, input_dir: str | None = None) -> dict | None:
        state_paths = cls.get_state_file_paths(input_dir)
        for sf_path in state_paths:
            if os.path.exists(sf_path):
                try:
                    with open(sf_path, "r", encoding="utf-8") as sf:
                        state_data = json.load(sf)
                        if input_dir:
                            if state_data.get("input_dir") == input_dir:
                                return state_data
                        else:
                            return state_data
                except Exception:
                    pass
        return None

    @classmethod
    def restore_or_create(
        cls, options, observer: ExtractionObserver | None = None
    ) -> "ExtractionSession":
        state = cls.load_state(options.BASE_PATH)
        session = cls(observer)
        session.input_dir = options.BASE_PATH
        session.output_file = options.OUTPUT_CSV
        session.regex_file = options.REGEX_FILE

        if state and options.RESUME:
            session.processed_files = state.get("processed_files", [])
            session.successful_pages = state.get("successful_pages", 0)
            session.failed_pages = state.get("failed_pages", 0)
            session.total_pages = state.get("total_pages", 0)
        return session

    def save_state(self) -> None:
        state_paths = self.get_state_file_paths(self.input_dir)
        state_data = {
            "input_dir": self.input_dir,
            "output_file": self.output_file,
            "regex_file": self.regex_file,
            "processed_files": self.processed_files,
            "successful_pages": self.successful_pages,
            "failed_pages": self.failed_pages,
            "total_pages": self.total_pages,
        }
        for sf_path in state_paths:
            try:
                with open(sf_path, "w", encoding="utf-8") as sf:
                    json.dump(state_data, sf, indent=4)
            except Exception:
                pass

    def clear_state(self) -> None:
        state_paths = self.get_state_file_paths(self.input_dir)
        for sf_path in state_paths:
            if os.path.exists(sf_path):
                try:
                    os.remove(sf_path)
                except Exception:
                    pass


class NoOpExtractionSession(ExtractionSession):
    def __init__(self):
        super().__init__()

    def start(self, total_files: int):
        pass

    def start_file(self, file_index: int, file_path: str):
        pass

    def start_page(self, page_index: int, total_pages: int):
        pass

    def process_page_result(self, success: bool, page_index: int, total_pages: int):
        pass

    def complete_file(self, file_index: int):
        pass

    def complete(self):
        pass

    def error(self, error_message: str):
        pass
