import time
from typing import cast
from pyingestion.observer import ExtractionObserver, DefaultExtractionObserver


class ExtractionSession:
    def __init__(
        self,
        observer: ExtractionObserver | None = None,
        error_handler=None,
    ):
        self.observer = observer or DefaultExtractionObserver()
        self.error_handler = error_handler
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
        self.config_file: str | None = None

        self.estimative_acc: float = 1200.0
        self.estimative_cnt: int = 1
        self._file_start_time: float = 0.0

    def save(self, source: str) -> None:  # pyright: ignore[reportUnusedParameter]
        pass

    def clear(self, source: str) -> None:  # pyright: ignore[reportUnusedParameter]
        pass

    @classmethod
    def load(cls, source: str) -> dict[str, object] | None:  # pyright: ignore[reportUnusedParameter]
        return None

    def log_failed_page(
        self,
        page_text: str,
        page_number: int,
        error_msg: str,
        extracted_data: dict[str, str] | None = None,
    ):
        if self.error_handler:
            self.error_handler(page_text, page_number, error_msg, extracted_data)

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


class FileExtractionSession(ExtractionSession):
    @classmethod
    def _get_paths(cls, source: str) -> list[str]:
        import os

        paths = [os.path.join(os.getcwd(), ".gaia_resume.json")]
        if os.path.exists(source):
            if os.path.isdir(source):
                paths.append(os.path.join(source, ".gaia_resume.json"))
            else:
                paths.append(
                    os.path.join(
                        os.path.dirname(os.path.abspath(source)),
                        ".gaia_resume.json",
                    )
                )
        return list(set(paths))

    @classmethod
    def load(cls, source: str) -> dict[str, object] | None:
        import os
        import json

        paths = cls._get_paths(source)
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        state_data = cast(dict[str, object], json.load(f))
                        # Ensure compatibility keys
                        if (
                            "regex_file" in state_data
                            and "config_file" not in state_data
                        ):
                            state_data["config_file"] = state_data["regex_file"]
                        elif (
                            "config_file" in state_data
                            and "regex_file" not in state_data
                        ):
                            state_data["regex_file"] = state_data["config_file"]

                        if state_data.get("input_dir") == source:
                            return state_data
                except Exception:
                    pass
        return None

    def save(self, source: str) -> None:
        import json

        paths = self._get_paths(source)
        state_data = {
            "input_dir": source,
            "output_file": self.output_file,
            "config_file": self.config_file,
            "regex_file": self.config_file,
            "processed_files": self.processed_files,
            "successful_pages": self.successful_pages,
            "failed_pages": self.failed_pages,
            "total_pages": self.total_pages,
        }
        for p in paths:
            try:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, indent=4)
            except Exception:
                pass

    def clear(self, source: str) -> None:
        import os

        paths = self._get_paths(source)
        for p in paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
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

    def save(self, source: str) -> None:
        pass

    def clear(self, source: str) -> None:
        pass
