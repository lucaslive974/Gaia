import os
from config.settings import Settings
from core.extractor import NativePdfExtractor
from core.ocr_parser import DefaultOcrParser
from core.csv_writer import DefaultCsvWriter
from core.observer import ExtractionObserver


class ShellManager:
    """
    Manager class responsible for orchestrating the CLI execution logic,
    directory validations, PDF parsing queue, and final output reporting.
    """

    def __init__(self, observer: ExtractionObserver | None = None):
        self.observer = observer

    def run(self, settings: Settings) -> bool:
        # 1. Validations
        if not os.path.exists(settings.BASE_PATH):
            if self.observer:
                self.observer.on_error(
                    f"O diretório de entrada '{settings.BASE_PATH}' não existe."
                )
            return False

        if not os.path.isdir(settings.BASE_PATH):
            if self.observer:
                self.observer.on_error(
                    f"O caminho de entrada '{settings.BASE_PATH}' não é um diretório."
                )
            return False

        # 2. Create destination output CSV directory
        output_dir = os.path.dirname(settings.OUTPUT_CSV)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 3. Clean up previous gaia_errors.log if not in resume mode
        log_path = os.path.join(os.getcwd(), "gaia_errors.log")
        if not settings.RESUME and os.path.exists(log_path):
            try:
                os.remove(log_path)
            except Exception:
                pass

        # 4. Instantiate parser engines
        extractor = NativePdfExtractor()
        csv_writer = DefaultCsvWriter(path_output=settings.OUTPUT_CSV)
        ocr_parser = DefaultOcrParser(extractor=extractor, csv_writer=csv_writer)

        try:
            ocr_parser.process(settings.BASE_PATH, self.observer, resume=settings.RESUME)
        except Exception as e:
            if self.observer:
                self.observer.on_error(f"Erro crítico durante o processamento: {e}")
            return False

        return True

