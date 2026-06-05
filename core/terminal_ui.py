import os
import sys
from typing import override
from core.observer import ExtractionObserver
from rich.console import Console, Group
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

try:
    import termios
    import select
    import tty
except ImportError:
    termios = None
    select = None
    tty = None


class TerminalManager:
    """
    Context manager to persistently configure the terminal in non-canonical
    and non-echo mode during execution, while preserving signals (Ctrl+C).
    Restores the original terminal attributes automatically upon exiting.
    """

    def __init__(self):
        self._old_settings = None

    def __enter__(self):
        if termios is None:
            return self
        try:
            fd = sys.stdin.fileno()
            if os.isatty(fd):
                self._old_settings = termios.tcgetattr(fd)
                new_settings = termios.tcgetattr(fd)
                # Disable ICANON (canonical mode) and ECHO (echo input)
                # Keep ISIG (signals) active so Ctrl+C raises KeyboardInterrupt
                new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO
                termios.tcsetattr(fd, termios.TCSANOW, new_settings)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if termios is None or self._old_settings is None:
            return
        try:
            fd = sys.stdin.fileno()
            if os.isatty(fd):
                termios.tcsetattr(fd, termios.TCSANOW, self._old_settings)
        except Exception:
            pass


class ConsoleObserver(ExtractionObserver):
    """
    TUI Observer that updates rich.progress and rich.live in real-time,
    handling terminal display rendering and ESC key cancellation.
    """

    def __init__(self, console: Console, progress: Progress):
        self.console = console
        self.progress = progress
        self.live = None
        self.total_files = 0
        self.file_index = 0
        self.current_file_name = "Nenhum"
        self.total_pages = 0
        self.successful_pages = 0
        self.native_pages = 0
        self.ocr_pages = 0
        self.error_pages = 0
        self.current_page = 0
        self.total_current_pages = 0
        self.method = ""
        self.is_cancelled = False

        self.total_files_task = self.progress.add_task(
            "[cyan]Progresso dos Arquivos", total=0
        )
        self.current_file_task = self.progress.add_task(
            "[magenta]Progresso das Páginas", total=0
        )

    def set_live(self, live: Live):
        self.live = live

    def _update_live(self):
        if self.live is not None:
            self.live.update(self.get_renderable())

    def _check_cancel_keys(self) -> bool:
        if select is None:
            return False
        try:
            fd = sys.stdin.fileno()
            if not os.isatty(fd):
                return False
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == "\x1b":  # ESC key code
                    return True
        except Exception:
            pass
        return False

    @override
    def on_start(self, total_files: int):
        self.total_files = total_files
        self.progress.update(self.total_files_task, total=total_files, completed=0)
        self._update_live()

    @override
    def on_file_start(self, file_index: int, file_path: str, estimated_hours: float):
        if not self.is_cancelled and self._check_cancel_keys():
            self.is_cancelled = True
        self.file_index = file_index
        self.current_file_name = os.path.basename(file_path)
        self.estimated_hours = estimated_hours
        self.progress.update(
            self.current_file_task,
            total=0,
            completed=0,
            description=f"[magenta]Páginas de {self.current_file_name}",
        )
        self._update_live()

    @override
    def on_page_start(self, page_index: int, total_pages: int):
        if not self.is_cancelled and self._check_cancel_keys():
            self.is_cancelled = True
        self.current_page = page_index
        self.total_current_pages = total_pages
        self.progress.update(self.current_file_task, total=total_pages)
        self._update_live()

    @override
    def on_page_processed(
        self,
        success: bool,
        extracted_pages: int,
        error_pages: int,
        page_index: int,
        total_pages: int,
        native_pages: int,
        ocr_pages: int,
        method: str,
    ):
        self.successful_pages = extracted_pages
        self.error_pages = error_pages
        self.native_pages = native_pages
        self.ocr_pages = ocr_pages
        self.current_page = page_index
        self.method = method
        self.progress.update(self.current_file_task, completed=page_index)
        self._update_live()

    @override
    def on_file_complete(self, file_index: int, progress_percent: float):
        self.progress.update(self.total_files_task, completed=file_index)
        self._update_live()

    @override
    def on_complete(self, successful_pages: int, total_pages: int):
        if self.current_file_task is not None:
            self.progress.remove_task(self.current_file_task)
        self._update_live()

    @override
    def on_error(self, error_message: str):
        if self.live is not None:
            self.live.console.print(f"[bold red]🚨 ERRO: {error_message}[/bold red]")
        else:
            self.console.print(f"[bold red]🚨 ERRO: {error_message}[/bold red]")

    def get_renderable(self) -> Group:
        if hasattr(self, "estimated_hours") and self.estimated_hours > 0:
            if self.estimated_hours >= 1.0:
                eta_str = f"{self.estimated_hours:.2f}h"
            else:
                eta_str = f"{round(self.estimated_hours * 60)} min"
        else:
            eta_str = "--:--"

        # Construct a clean status block with emojis and colors (non-tabular layout)
        status_text = (
            f"[bold green]📊 Painel de Extração (Gaia)[/bold green]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 [bold cyan]Arquivos Processados:[/bold cyan] {self.file_index} de {self.total_files}\n"
            f"📄 [bold blue]Páginas Nativas (Leve):[/bold blue] {self.native_pages}\n"
            f"🤖 [bold yellow]Páginas OCR (Tesseract):[/bold yellow] {self.ocr_pages}\n"
            f"🚨 [bold red]Falhas de Leitura:[/bold red] {self.error_pages}\n"
            f"⏳ [bold white]Tempo Restante Estimado:[/bold white] {eta_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 [bold magenta]Arquivo Atual:[/bold magenta] [white]{self.current_file_name}[/white]"
        )

        if self.method:
            method_str = (
                "[cyan]Nativo[/cyan]"
                if self.method == "native"
                else "[yellow]OCR[/yellow]"
            )
            status_text += f" [dim]({method_str})[/dim]"

        status_panel = Panel(status_text, border_style="green", expand=True)

        return Group(status_panel, self.progress)


def print_summary_dashboard(
    console: Console,
    total_files: int,
    total_pages: int,
    successful_pages: int,
    native_pages: int,
    ocr_pages: int,
    elapsed_time: float,
):
    table = Table(
        title="[bold green]📊 Resumo da Extração[/bold green]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green", justify="right")

    table.add_row("Arquivos Processados", str(total_files))
    table.add_row("Total de Páginas", str(total_pages))
    table.add_row("Páginas Nativas (Leve/Rápido)", f"[blue]{native_pages}[/blue]")
    table.add_row("Páginas OCR Tesseract (Pesado)", f"[yellow]{ocr_pages}[/yellow]")
    table.add_row("Falhas de Extração", f"[red]{total_pages - successful_pages}[/red]")
    table.add_row("Tempo Total Decorrido", f"{(elapsed_time / (60 * 60)):.0f} segundos")

    console.print("\n")
    console.print(table)
