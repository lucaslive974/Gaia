import csv
from os import path
from abc import ABC, abstractmethod
from gaia.config import settings


class CsvWriter(ABC):
    @abstractmethod
    def write(self, content: dict[str, str]):
        pass


class DefaultCsvWriter(CsvWriter):
    def __init__(self, path_output: str | None = None):
        self._writer = None
        self._path = path_output

    def write(self, content: dict[str, str]):
        output_path = self._path or settings["OUTPUT_CSV"]
        file_exists = path.exists(output_path)
        
        with open(output_path, mode="a", newline="", encoding="utf-8") as csv_file:
            self._writer = csv.DictWriter(csv_file, fieldnames=content.keys(), skipinitialspace=True)
            if not file_exists:
                self._writer.writeheader()
            self._writer.writerow(content)
