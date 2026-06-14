import csv
from os import path
from abc import ABC, abstractmethod
from pyingestion.options import options


class OutputStream(ABC):
    @abstractmethod
    def write(self, content: dict[str, str]):
        pass


class CsvWriteStream(OutputStream):
    def __init__(self, path_output: str | None = None):
        self._path = path_output

    def write(self, content: dict[str, str]):
        output_path = self._path or options["OUTPUT_CSV"]
        file_exists = path.exists(output_path)

        with open(output_path, mode="a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file, fieldnames=content.keys(), skipinitialspace=True
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(content)


class DefaultOutputStream(OutputStream):
    def __init__(self):
        self._data = []

    def write(self, content: dict[str, str]):
        self._data.append(content)

    def __iter__(self):
        for item in self._data:
            yield item
