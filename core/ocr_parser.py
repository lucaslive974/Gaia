import re
import time
import unicodedata
from os import path, listdir
from abc import ABC, abstractmethod

from core.extractor import BasePdfExtractor, FallbackPdfExtractor
from core.csv_writer import CsvWriter, DefaultCsvWriter
from core.observer import ExtractionObserver


class OcrParser(ABC):
    @abstractmethod
    def process(self, dir_path: str, observer: ExtractionObserver | None = None):
        pass


class DefaultOcrParser(OcrParser):
    _DATE = r"\d{2}/\d{2}/\d{4}"
    _RE_KVP = re.compile(
        rf"""
        Data\s+de\s+Emissao\s+(?P<DAT_EMISS>{_DATE})
        .*?
        Data\s+do\s+Vencimento\s+(?P<DAT_VENC>{_DATE})
        .*?
        N\s*Auto\s+de\s+Infracao:?\s+(?P<AI>\w{{6,7}})
        .*?
        (Concessionaria:?\s+(?P<CONC>[\w\s\-]+?)\s+Lancamento
        .*?
        Linha:\s+(?P<LINHA>[\w\s/\-|]+?)
        \s+Veiculo:\s*(?P<VEIC>\d{{4,6}})?
        \s+Placa:\s*(?P<PLACA>[A-Z0-9]{{7}})?
        \s+Data:\s+(?P<DAT_OCC>{_DATE})
        \s+Hora:\s+(?P<HORA_OCC>\d{{2}}:\d{{2}})
        \s+Local:\s+(?P<LOCAL>.*)\s+Base\s+legal
        .*?
        Descricao\s+da\s+infracao:\s+(?P<DESC>[^.]+)
        .*?)?
        Valor:\s+R\$\s*(?P<VALOR>[\d.,]+)
        """, re.DOTALL | re.IGNORECASE | re.VERBOSE
    )

    def __init__(self,
                 extractor: BasePdfExtractor | None = None,
                 csv_writer: CsvWriter | None = None):
        self._extractor = extractor or FallbackPdfExtractor()
        self._csv_writer = csv_writer or DefaultCsvWriter()

        self._estimative_acc = 1200
        self._estimative_cnt = 1
        self._total_pages = 0
        self._successful_pages = 0
        self._native_pages = 0
        self._ocr_pages = 0

    def process(self, dir_path: str, observer: ExtractionObserver | None = None):
        self._verify_path(dir_path)
        self._total_pages = 0
        self._successful_pages = 0
        self._native_pages = 0
        self._ocr_pages = 0

        try:
            files = [f for f in listdir(dir_path) if f.lower().endswith(".pdf")]
        except Exception as e:
            if observer:
                observer.on_error(f"Erro ao listar o diretório: {e}")
            raise e

        total_files = len(files)
        if total_files == 0:
            if observer:
                observer.on_error("Nenhum arquivo PDF encontrado no diretório selecionado.")
            return

        if observer:
            observer.on_start(total_files)

        for file_index, file in enumerate(files, start=1):
            if observer and getattr(observer, "is_cancelled", False):
                break

            start_time = time.perf_counter()
            file_path = path.join(dir_path, file)

            # Calculate estimation
            _estimative = round(self._estimative_acc / self._estimative_cnt)
            total_estimative = total_files * _estimative
            est_hours = round((total_estimative - (file_index * _estimative)) / 3600.0, 2)

            if observer:
                observer.on_file_start(file_index, file_path, est_hours)

            try:
                self._process_file(file_path, observer)
            except Exception as e:
                if observer:
                    observer.on_error(f"Erro no arquivo {file}: {e}")
                continue

            if observer:
                progress_percent = (file_index / total_files) * 100
                observer.on_file_complete(file_index, progress_percent)

            self._estimative_acc += time.perf_counter() - start_time
            self._estimative_cnt += 1

        if observer:
            observer.on_complete(self._successful_pages, self._total_pages)

    def _process_file(self, file_path: str, observer: ExtractionObserver | None):
        total_pages = self._extractor.get_page_count(file_path)
        self._total_pages += total_pages

        page_generator = self._extractor.extract_pages(file_path)
        for page_index, (page_text, method) in enumerate(page_generator, start=1):
            if observer and getattr(observer, "is_cancelled", False):
                break

            if observer:
                observer.on_page_start(page_index, total_pages)

            success = self._process_page(page_text, page_index)
            if success:
                self._successful_pages += 1
                if method == "native":
                    self._native_pages += 1
                else:
                    self._ocr_pages += 1

            if observer:
                error_pages = self._total_pages - self._successful_pages
                observer.on_page_processed(
                    success,
                    self._successful_pages,
                    error_pages,
                    page_index,
                    total_pages,
                    self._native_pages,
                    self._ocr_pages,
                    method
                )

    def _process_page(self, page_text: str, page_number: int) -> bool:
        try:
            page_dict = self._parse_page(page_text)
            self._csv_writer.write(page_dict)
            return True
        except ValueError:
            return False

    def _parse_page(self, page_text: str) -> dict[str, str]:
        text_pos_processed = _pos_processing_text(page_text)
        match = re.search(self._RE_KVP, text_pos_processed)
        if not match:
            raise ValueError("Invalid page structure")
        return match.groupdict()

    def _verify_path(self, dir_path: str):
        if not path.exists(dir_path):
            raise FileNotFoundError("Diretório especificado não existe")


def _pos_processing_text(text: str) -> str:
    text = re.sub(r"[-—|°º]", " ", text)
    return unicodedata.normalize("NFD", text) \
        .encode("ascii", "ignore") \
        .decode("ascii")
