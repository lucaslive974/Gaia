import time
from collections.abc import Callable
from typing import cast

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from pyingestion.observer import EventBus, PipelineEvents


class ExtractionSession(BaseModel):
    # Serialized fields
    input_dir: str | None = None
    output_file: str | None = None
    config_file: str | None = None
    regex_file: str | None = None
    processed_files: list[str] = Field(default_factory=list)
    successful_pages: int = 0
    failed_pages: int = 0
    total_pages: int = 0

    total_files: int = 0
    file_index: int = 0
    current_file_path: str = ""

    # Non-serialized transient private attributes
    _bus: EventBus = PrivateAttr(default_factory=EventBus)
    _error_handler: Callable[..., object] | None = PrivateAttr(default=None)
    _estimative_acc: float = PrivateAttr(default=1200.0)
    _estimative_cnt: int = PrivateAttr(default=1)
    _file_start_time: float = PrivateAttr(default=0.0)
    _is_cancelled: bool = PrivateAttr(default=False)

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        error_handler: Callable[..., object] | None = None,
        bus: EventBus | None = None,
        **data: object,
    ):
        super().__init__(**data)
        if bus is not None:
            self._bus = bus
        if error_handler is not None:
            self._error_handler = error_handler

    @model_validator(mode="before")
    @classmethod
    def migrate_regex_file(cls, data: object) -> object:
        if isinstance(data, dict):
            if "regex_file" in data and "config_file" not in data:
                data["config_file"] = data["regex_file"]
            elif "config_file" in data and "regex_file" not in data:
                data["regex_file"] = data["config_file"]
        return data

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def error_handler(self) -> Callable[..., object] | None:
        return self._error_handler

    @error_handler.setter
    def error_handler(self, val: Callable[..., object] | None):
        self._error_handler = val

    @property
    def estimative_acc(self) -> float:
        return self._estimative_acc

    @estimative_acc.setter
    def estimative_acc(self, val: float):
        self._estimative_acc = val

    @property
    def estimative_cnt(self) -> int:
        return self._estimative_cnt

    @estimative_cnt.setter
    def estimative_cnt(self, val: int):
        self._estimative_cnt = val

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
        if self._error_handler:
            self._error_handler(page_text, page_number, error_msg, extracted_data)

    def start(self, total_files: int):
        self.total_files = total_files
        self.bus.emit(
            PipelineEvents.EXTRACTION_STARTED, session=self, total_files=total_files
        )

    def start_file(self, file_index: int, file_path: str):
        self.file_index = file_index
        self.current_file_path = file_path
        self._file_start_time = time.perf_counter()

        _estimative = round(self._estimative_acc / self._estimative_cnt)
        remaining_count = self.total_files - self.file_index + 1
        est_hours = round((remaining_count * _estimative) / 3600.0, 2)

        self.bus.emit(
            PipelineEvents.FILE_STARTED,
            session=self,
            file_index=file_index,
            file_path=file_path,
            estimated_hours=est_hours,
        )

    def start_page(self, page_index: int, total_pages: int):
        self.bus.emit(
            PipelineEvents.PAGE_STARTED,
            session=self,
            page_index=page_index,
            total_pages=total_pages,
        )

    def process_page_result(self, success: bool, page_index: int, total_pages: int):
        if success:
            self.successful_pages += 1
        else:
            self.failed_pages += 1

        self.bus.emit(
            PipelineEvents.PAGE_PROCESSED,
            session=self,
            success=success,
            extracted_pages=self.successful_pages,
            error_pages=self.failed_pages,
            page_index=page_index,
            total_pages=total_pages,
        )

    def complete_file(self, file_index: int):
        elapsed = time.perf_counter() - self._file_start_time
        self._estimative_acc += elapsed
        self._estimative_cnt += 1

        progress_percent = (
            (file_index / self.total_files) * 100 if self.total_files > 0 else 100.0
        )
        self.bus.emit(
            PipelineEvents.FILE_COMPLETED,
            session=self,
            file_index=file_index,
            progress_percent=progress_percent,
        )

    def complete(self):
        self.bus.emit(
            PipelineEvents.EXTRACTION_COMPLETED,
            session=self,
            successful_pages=self.successful_pages,
            total_pages=self.total_pages,
        )

    def error(self, error_message: str):
        self.bus.emit(
            PipelineEvents.EXTRACTION_ERROR, session=self, error_message=error_message
        )

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @is_cancelled.setter
    def is_cancelled(self, value: bool):
        self._is_cancelled = value


class FileExtractionSession(ExtractionSession):
    def __init__(
        self,
        error_handler: Callable[..., object] | None = None,
        bus: EventBus | None = None,
        **data: object,
    ):
        super().__init__(error_handler=error_handler, bus=bus, **data)

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
        import json
        import os

        paths = cls._get_paths(source)
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        state_data = cast(dict[str, object], json.load(f))
                        # Validate using model validator and return serialized dict
                        validated = cls.model_validate(state_data)
                        res = validated.model_dump()

                        # Ensure compatibility keys
                        if "regex_file" in res and "config_file" not in res:
                            res["config_file"] = res["regex_file"]
                        elif "config_file" in res and "regex_file" not in res:
                            res["regex_file"] = res["config_file"]

                        if res.get("input_dir") == source:
                            return res
                except Exception:
                    pass
        return None

    def save(self, source: str) -> None:
        import json

        paths = self._get_paths(source)
        state_data = self.model_dump()
        state_data["input_dir"] = source
        state_data["output_file"] = self.output_file
        state_data["config_file"] = self.config_file
        state_data["regex_file"] = self.config_file

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
    def __init__(
        self,
        error_handler: Callable[..., object] | None = None,
        bus: EventBus | None = None,
        **data: object,
    ):
        super().__init__(error_handler=error_handler, bus=bus, **data)

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
