import os
from abc import ABC, abstractmethod
from typing import Generic
from collections.abc import Generator
from pyingestion.extraction_session import ExtractionSession
from pyingestion.types import T_source, T_in


class InputStream(Generic[T_source, T_in], ABC):
    """
    Abstract Base Class representing a generic input stream.
    Its responsibility is to read from a source and yield text units.
    """

    current_unit_index: int = 0
    total_units: int = 0

    @abstractmethod
    def read(
        self, source: T_source, session: ExtractionSession | None = None
    ) -> Generator[T_in, None, None]:
        """
        Reads from the source, updates the session, and yields groups (units) of text.
        """
        pass


class FileInputStream(InputStream[str, str], ABC):
    """
    Abstract Base Class representing a file-system based input stream.
    """

    @abstractmethod
    def accepts(self, file_path: str) -> bool:
        """
        Returns True if the stream supports the file extension, False otherwise.
        """
        pass

    def _find_files(self, source: str) -> list[str]:
        if os.path.isfile(source):
            if self.accepts(source):
                return [os.path.basename(source)]
            return []

        files = []
        if getattr(self, "recursive", False):
            for root, _, filenames in os.walk(source):
                for f in filenames:
                    full_path = os.path.join(root, f)
                    if self.accepts(full_path):
                        rel_path = os.path.relpath(full_path, source)
                        files.append(rel_path)
        else:
            try:
                for f in os.listdir(source):
                    full_path = os.path.join(source, f)
                    if self.accepts(full_path):
                        files.append(f)
            except Exception:
                pass

        files.sort()
        return files
