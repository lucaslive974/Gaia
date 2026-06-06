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
        self.error_pages = 0
        self.current_page = 0
        self.total_current_pages = 0
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
    ):
        self.successful_pages = extracted_pages
        self.error_pages = error_pages
        self.current_page = page_index
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
            f"📄 [bold blue]Páginas com Sucesso:[/bold blue] {self.successful_pages}\n"
            f"🚨 [bold red]Falhas de Leitura:[/bold red] {self.error_pages}\n"
            f"⏳ [bold white]Tempo Restante Estimado:[/bold white] {eta_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 [bold magenta]Arquivo Atual:[/bold magenta] [white]{self.current_file_name}[/white]"
        )

        status_panel = Panel(status_text, border_style="green", expand=True)

        return Group(status_panel, self.progress)


def print_summary_dashboard(
    console: Console,
    total_files: int,
    total_pages: int,
    successful_pages: int,
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
    table.add_row("Páginas Processadas com Sucesso", f"[blue]{successful_pages}[/blue]")
    table.add_row("Falhas de Extração", f"[red]{total_pages - successful_pages}[/red]")
    table.add_row("Tempo Total Decorrido", f"{elapsed_time:.2f} segundos")

    console.print("\n")
    console.print(table)


def run_with_ui(settings):
    from core.shell_manager import ShellManager
    import time
    from rich.progress import (
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeRemainingColumn,
    )

    console = Console()
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    observer = ConsoleObserver(console, progress)
    shell = ShellManager(observer)

    start_time = time.perf_counter()

    with TerminalManager():
        with Live(
            observer.get_renderable(), console=console, refresh_per_second=10
        ) as live:
            observer.set_live(live)
            try:
                success = shell.run(settings)
            except KeyboardInterrupt:
                observer.is_cancelled = True
                success = False

    if observer.is_cancelled:
        console.print(
            "\n[bold yellow]⚠️ Processamento cancelado pelo usuário (Ctrl+C ou ESC).[/bold yellow]\n"
        )
        sys.exit(0)

    if not success:
        sys.exit(1)

    elapsed_time = time.perf_counter() - start_time
    total_pages = observer.successful_pages + observer.error_pages

    print_summary_dashboard(
        console=console,
        total_files=observer.file_index,
        total_pages=total_pages,
        successful_pages=observer.successful_pages,
        elapsed_time=elapsed_time,
    )

    log_path = os.path.join(os.getcwd(), "gaia_errors.log")
    if observer.successful_pages < total_pages:
        console.print(
            f"\n[bold red]⚠️ Atenção: {total_pages - observer.successful_pages} página(s) falharam na extração.[/bold red]"
        )
        console.print(
            f"[yellow]O texto extraído das páginas com falha foi salvo em: [bold]{log_path}[/bold][/yellow]\n"
        )
    else:
        console.print(
            "\n[bold green]🎉 Processamento concluído com 100% de sucesso![/bold green]\n"
        )


def run_test_mode(settings):
    import sys
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from core.regex_engine import NativeRegexEngine
    from core.extractor import NativePdfExtractor
    from core.ocr_parser import _pos_processing_text

    console = Console()
    console.print(
        Panel("[bold green]🧪 Gaia - Modo de Teste de Regex[/bold green]", expand=False)
    )

    pdf_path = settings.TEST_FILE
    regex_path = settings.REGEX_FILE

    console.print(f"[bold cyan]Arquivo PDF:[/bold cyan] {pdf_path}")
    console.print(f"[bold cyan]Arquivo Regex:[/bold cyan] {regex_path}")

    # 1. Load Regex Engine
    try:
        engine = NativeRegexEngine(regex_path)
    except Exception as e:
        console.print(
            f"\n[bold red]❌ Erro ao carregar as regras de regex:[/bold red] {e}"
        )
        sys.exit(1)

    # 2. Extract First Page Text
    try:
        extractor = NativePdfExtractor()
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

        pages = list(extractor.extract_pages(pdf_path))
        if not pages:
            raise ValueError("O arquivo PDF não contém páginas.")

        raw_text = pages[0]
        normalized_text = _pos_processing_text(raw_text)
    except Exception as e:
        console.print(
            f"\n[bold red]❌ Erro ao ler a primeira página do PDF:[/bold red] {e}"
        )
        sys.exit(1)

    # Print a snippet of normalized text to help debug
    console.print(
        "\n[bold yellow]--- Início do Texto Normalizado da Primeira Página ---[/bold yellow]"
    )
    snippet = normalized_text[:500]
    console.print(snippet)
    if len(normalized_text) > 500:
        console.print("...")
    console.print(
        "[bold yellow]--- Fim do Texto Normalizado da Primeira Página ---[/bold yellow]\n"
    )

    # 3. Match patterns
    results, matched_status = engine.parse_test(normalized_text)

    # 4. Render Table of Results
    table = Table(
        title="[bold green]📋 Resultados do Casamento de Padrões[/bold green]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Campo", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Valor Extraído", style="green")
    table.add_column("Obrigatoriedade", justify="center")
    table.add_column("Expressão Regular", style="dim")

    has_missing_required = False
    missing_required_fields = []

    for key, entry in engine.patterns.items():
        matched = matched_status[key]
        required = entry["required"]
        val = results[key]
        regex_str = entry["regex_str"]

        status_str = (
            "[green]CORRESPONDIDO[/green]" if matched else "[red]NÃO ENCONTRADO[/red]"
        )
        req_str = "[bold red]Sim[/bold red]" if required else "Não"

        if required and not val:
            has_missing_required = True
            missing_required_fields.append(key)
            status_str = "[bold red]AUSENTE[/bold red]"

        val_display = val if val else f"[dim](default: '{entry['default']}')[/dim]"

        table.add_row(key, status_str, val_display, req_str, regex_str)

    console.print(table)

    if has_missing_required:
        console.print(
            f"\n[bold red]❌ Falha: Os seguintes campos obrigatórios não foram extraídos: {', '.join(missing_required_fields)}[/bold red]"
        )
        sys.exit(1)
    else:
        console.print(
            "\n[bold green]🎉 Sucesso: Todos os campos obrigatórios foram extraídos com sucesso![/bold green]"
        )
        sys.exit(0)

