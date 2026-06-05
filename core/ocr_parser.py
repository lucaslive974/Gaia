import re
import time
import os
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
    _RE_KVP = {
        "data_emissao": re.compile(
            rf"""Data\s+de\s+Emiss[ãa]o\s+({_DATE})""", re.IGNORECASE | re.VERBOSE
        ),
        "data_vencimento": re.compile(
            rf"""Data\s+d[eo]\s+Vencimento\s+({_DATE})""", re.IGNORECASE | re.VERBOSE
        ),
        "n_infracao": re.compile(
            r"""Auto\s+de\s+Infra[cç][ãa]o:?\s+([A-Z0-9]{6,7})""",
            re.IGNORECASE | re.VERBOSE,
        ),
        "concessionaria": re.compile(
            r"""Concession[áa]ria:?\s+([\w\s\-]+?)\s+Lan[cç]amento""",
            re.IGNORECASE | re.VERBOSE,
        ),
        "linha": re.compile(
            r"""Linha:\s+([\w\s/\-|]+?)(?=\s+Ve[íi]culo|\s+Placa|\s*$)""",
            re.IGNORECASE | re.VERBOSE,
        ),
        "veiculo": re.compile(
            r"""Ve[íi]culo:\s*(\d{4,6})""", re.IGNORECASE | re.VERBOSE
        ),
        "placa": re.compile(r"""Placa:\s*([A-Z0-9]{7})""", re.IGNORECASE | re.VERBOSE),
        "data_ocorrencia": re.compile(
            rf"""Data:\s+({_DATE})""", re.IGNORECASE | re.VERBOSE
        ),
        "hora_ocorrencia": re.compile(
            r"""Hora:\s+(\d{2}:\d{2})""", re.IGNORECASE | re.VERBOSE
        ),
        "local": re.compile(
            r"""Local:\s+(.*?)\s+Base\s+legal""", re.IGNORECASE | re.DOTALL | re.VERBOSE
        ),
        "descricao": re.compile(
            r"""Descri[cç][ãa]o\s+da\s+infra[cç][ãa]o:\s+([^.]+)""",
            re.IGNORECASE | re.VERBOSE,
        ),
        "valor": re.compile(
            r"""Valor:\s+R\$\s*([\d.,]+)""", re.IGNORECASE | re.VERBOSE
        ),
    }

    def __init__(
        self,
        extractor: BasePdfExtractor | None = None,
        csv_writer: CsvWriter | None = None,
    ):
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
                observer.on_error(
                    "Nenhum arquivo PDF encontrado no diretório selecionado."
                )
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
            est_hours = round(
                (total_estimative - (file_index * _estimative)) / 3600.0, 2
            )

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
                    method,
                )

    def _process_page(self, page_text: str, page_number: int) -> bool:
        try:
            page_dict = self._parse_page(page_text)
            self._csv_writer.write(page_dict)
            return True
        except ValueError as e:
            extracted_data = getattr(e, "extracted_data", None)
            self._log_failed_page(page_text, page_number, str(e), extracted_data)
            return False

    def _log_failed_page(self, page_text: str, page_number: int, error_msg: str, extracted_data: dict[str, str] | None = None):
        log_path = os.path.join(os.getcwd(), "gaia_errors.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"FALHA NA EXTRAÇÃO - Página {page_number}\n")
                f.write(f"Erro: {error_msg}\n")
                if extracted_data:
                    f.write(f"Campos extraídos: {extracted_data}\n")
                f.write(f"{'-'*80}\n")
                f.write(page_text)
                f.write(f"\n{'='*80}\n")
        except Exception:
            pass

    def _parse_page(self, page_text: str) -> dict[str, str]:
        # Aplica o seu pré-processamento normal
        text_pos_processed = _pos_processing_text(page_text)

        resultados = {}
        posicao_atual = 0

        for chave, padrao in self._RE_KVP.items():
            match = padrao.search(text_pos_processed, pos=posicao_atual)

            if match:
                resultados[chave] = match.group(1).strip()
                # Move o ponteiro para o final do texto encontrado
                posicao_atual = match.end()
            else:
                # Retorna string vazia (ou None) se o OCR falhar em um campo específico
                resultados[chave] = ""

        # Validação: se não encontrou o campo principal, a página é inválida/lixo
        if not resultados.get("n_infracao"):
            err = ValueError("Invalid page structure: missing n_infracao")
            err.extracted_data = resultados
            raise err

        return resultados

    def _verify_path(self, dir_path: str):
        if not path.exists(dir_path):
            raise FileNotFoundError("Diretório especificado não existe")


def _pos_processing_text(text: str) -> str:
    text = re.sub(r"[-—|°º]", " ", text)
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")
