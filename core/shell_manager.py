import os
import sys
import time
from config.settings import Settings
from core.extractor import NativePdfExtractor
from core.ocr_parser import DefaultOcrParser
from core.csv_writer import DefaultCsvWriter
from core.terminal_ui import TerminalManager, ConsoleObserver, print_summary_dashboard
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.live import Live


class ShellManager:
    """
    Manager class responsible for orchestrating the CLI execution logic,
    directory validations, PDF parsing queue, and final output reporting.
    """

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def run(self, _settings: Settings | None = None):
        settings = _settings or Settings()

        # 1. Validations
        if not os.path.exists(settings.BASE_PATH):
            self.console.print(
                f"[bold red]Erro:[/bold red] O diretório de entrada '{settings.BASE_PATH}' não existe."
            )
            sys.exit(1)

        if not os.path.isdir(settings.BASE_PATH):
            self.console.print(
                f"[bold red]Erro:[/bold red] O caminho de entrada '{settings.BASE_PATH}' não é um diretório."
            )
            sys.exit(1)

        # 3. Create destination output CSV directory
        output_dir = os.path.dirname(settings.OUTPUT_CSV)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 4. Clean up previous gaia_errors.log
        log_path = os.path.join(os.getcwd(), "gaia_errors.log")
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
            except Exception:
                pass

        # 5. Instantiate parser engines
        extractor = NativePdfExtractor()
        csv_writer = DefaultCsvWriter(path_output=settings.OUTPUT_CSV)
        ocr_parser = DefaultOcrParser(extractor=extractor, csv_writer=csv_writer)

        start_time = time.perf_counter()

        # 6. Set up terminal progress bar (TUI)
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )
        observer = ConsoleObserver(self.console, progress)

        # 7. Execute within the TerminalManager and Live context
        with TerminalManager():
            with Live(
                observer.get_renderable(), console=self.console, refresh_per_second=10
            ) as live:
                observer.set_live(live)
                try:
                    ocr_parser.process(settings.BASE_PATH, observer)
                except KeyboardInterrupt:
                    observer.is_cancelled = True
                except Exception as e:
                    self.console.print(
                        f"[bold red]🚨 Erro crítico durante o processamento: {e}[/bold red]"
                    )
                    sys.exit(1)

        # 8. Handle cancel warning
        if observer.is_cancelled:
            self.console.print(
                "\n[bold yellow]⚠️ Processamento cancelado pelo usuário (Ctrl+C ou ESC).[/bold yellow]\n"
            )
            sys.exit(0)

        elapsed_time = time.perf_counter() - start_time

        # 9. Display summary dashboard
        total_pages = ocr_parser._total_pages
        successful_pages = ocr_parser._successful_pages
        native_pages = ocr_parser._native_pages
        ocr_pages = ocr_parser._ocr_pages

        # Count target files
        total_files = len(
            [f for f in os.listdir(settings["BASE_PATH"]) if f.lower().endswith(".pdf")]
        )

        print_summary_dashboard(
            console=self.console,
            total_files=total_files,
            total_pages=total_pages,
            successful_pages=successful_pages,
            native_pages=native_pages,
            ocr_pages=ocr_pages,
            elapsed_time=elapsed_time,
        )

        if successful_pages < total_pages:
            self.console.print(
                f"\n[bold red]⚠️ Atenção: {total_pages - successful_pages} página(s) falharam na extração.[/bold red]"
            )
            self.console.print(
                f"[yellow]O texto extraído das páginas com falha foi salvo em: [bold]{log_path}[/bold][/yellow]\n"
            )
        else:
            self.console.print(
                "\n[bold green]🎉 Processamento concluído com 100% de sucesso![/bold green]\n"
            )
