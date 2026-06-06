import time
from core.observer import ExtractionObserver, DefaultExtractionObserver


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
