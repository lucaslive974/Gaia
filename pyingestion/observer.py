import queue
from abc import ABC, abstractmethod
from typing import override


class ExtractionObserver(ABC):
    is_cancelled: bool = False

    @abstractmethod
    def on_start(self, total_files: int):
        """Called when the extraction process starts."""

    @abstractmethod
    def on_file_start(self, file_index: int, file_path: str, estimated_hours: float):
        """Called when processing of a specific file starts."""

    @abstractmethod
    def on_page_start(self, page_index: int, total_pages: int):
        """Called when a page is about to be processed."""

    @abstractmethod
    def on_page_processed(
        self,
        success: bool,
        extracted_pages: int,
        error_pages: int,
        page_index: int,
        total_pages: int,
    ):
        """Called after a page has been processed."""

    @abstractmethod
    def on_file_complete(self, file_index: int, progress_percent: float):
        """Called when a file is fully processed."""

    @abstractmethod
    def on_complete(self, successful_pages: int, total_pages: int):
        """Called when the entire queue of files is completed."""

    @abstractmethod
    def on_error(self, error_message: str):
        """Called when a critical error occurs."""


class QueueObserver(ExtractionObserver):
    """
    Thread-safe observer that puts events into a queue.Queue for UI consumption.
    """

    def __init__(self, event_queue: queue.Queue[tuple[str, object]]):
        self._queue = event_queue
        self.is_cancelled: bool = False

    @override
    def on_start(self, total_files: int):
        self._queue.put(("START", total_files))

    @override
    def on_file_start(self, file_index: int, file_path: str, estimated_hours: float):
        self._queue.put(("FILE_START", (file_index, file_path, estimated_hours)))

    @override
    def on_page_start(self, page_index: int, total_pages: int):
        self._queue.put(("PAGE_START", (page_index, total_pages)))

    @override
    def on_page_processed(
        self,
        success: bool,
        extracted_pages: int,
        error_pages: int,
        page_index: int,
        total_pages: int,
    ):
        self._queue.put(
            (
                "PAGE_PROCESSED",
                (success, extracted_pages, error_pages, page_index, total_pages),
            )
        )

    @override
    def on_file_complete(self, file_index: int, progress_percent: float):
        self._queue.put(("FILE_COMPLETE", (file_index, progress_percent)))

    @override
    def on_complete(self, successful_pages: int, total_pages: int):
        self._queue.put(("COMPLETE", (successful_pages, total_pages)))

    @override
    def on_error(self, error_message: str):
        self._queue.put(("ERROR", error_message))


class DefaultExtractionObserver(ExtractionObserver):
    """
    Default no-op implementation of ExtractionObserver.
    """

    def on_start(self, total_files: int):
        pass

    def on_file_start(self, file_index: int, file_path: str, estimated_hours: float):
        pass

    def on_page_start(self, page_index: int, total_pages: int):
        pass

    def on_page_processed(
        self,
        success: bool,
        extracted_pages: int,
        error_pages: int,
        page_index: int,
        total_pages: int,
    ):
        pass

    def on_file_complete(self, file_index: int, progress_percent: float):
        pass

    def on_complete(self, successful_pages: int, total_pages: int):
        pass

    def on_error(self, error_message: str):
        pass
