import os
import sys
from typing import override
from rich.console import Console, Group
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from pydocstructurer.observer import ExtractionObserver
from pydocstructurer.i18n import _, get_lang, Language

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
            "[cyan]" + _("ui_files_progress"), total=0
        )
        self.current_file_task = self.progress.add_task(
            "[magenta]" + _("ui_pages_progress"), total=0
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
            description="[magenta]" + _("ui_pages_of", filename=self.current_file_name),
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
        err_lbl = _("ui_error")
        if err_lbl == "ui_error":
            err_lbl = "🚨 ERROR"
        if self.live is not None:
            self.live.console.print(f"[bold red]{err_lbl}: {error_message}[/bold red]")
        else:
            self.console.print(f"[bold red]{err_lbl}: {error_message}[/bold red]")

    def get_renderable(self) -> Group:
        if hasattr(self, "estimated_hours") and self.estimated_hours > 0:
            if self.estimated_hours >= 1.0:
                eta_str = f"{self.estimated_hours:.2f}h"
            else:
                eta_str = f"{round(self.estimated_hours * 60)} min"
        else:
            eta_str = "--:--"

        # Construct a clean status block with emojis and colors (non-tabular layout)
        of_str = _("ui_of")
        if of_str == "ui_of":
            of_str = "of"
        status_text = (
            f"[bold green]{_('ui_dashboard_title')}[/bold green]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"[bold cyan]{_('ui_processed_files')}[/bold cyan] {self.file_index} {of_str} {self.total_files}\n"
            f"[bold blue]{_('ui_successful_pages')}[/bold blue] {self.successful_pages}\n"
            f"[bold red]{_('ui_extraction_failures')}[/bold red] {self.error_pages}\n"
            f"[bold white]{_('ui_estimated_time')}[/bold white] {eta_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"[bold magenta]{_('ui_current_file')}[/bold magenta] [white]{self.current_file_name}[/white]"
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
        title=f"[bold green]{_('ui_summary_title')}[/bold green]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column(_("ui_metric"), style="cyan")
    table.add_column(_("ui_value"), style="green", justify="right")

    table.add_row(_("ui_summary_processed_files"), str(total_files))
    table.add_row(_("ui_summary_total_pages"), str(total_pages))
    table.add_row(_("ui_summary_successful_pages"), f"[blue]{successful_pages}[/blue]")
    table.add_row(
        _("ui_summary_failures"), f"[red]{total_pages - successful_pages}[/red]"
    )

    seconds_str = _("ui_seconds")
    table.add_row(_("ui_summary_elapsed_time"), f"{elapsed_time:.2f} {seconds_str}")

    console.print("\n")
    console.print(table)


def run_with_ui(options):
    from pydocstructurer import PyDocStructurer, CsvWriteStream
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
    output_stream = CsvWriteStream(options.OUTPUT_CSV)
    controller = PyDocStructurer(options, observer=observer, output_stream=output_stream)

    start_time = time.perf_counter()

    with TerminalManager():
        with Live(
            observer.get_renderable(), console=console, refresh_per_second=10
        ) as live:
            observer.set_live(live)
            try:
                success = controller.run(options)
            except KeyboardInterrupt:
                observer.is_cancelled = True
                success = False

    if observer.is_cancelled:
        console.print(f"\n[bold yellow]{_('ui_cancelled_msg')}[/bold yellow]\n")
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
            f"\n[bold red]{_('ui_warning_failed_pages', count=total_pages - observer.successful_pages)}[/bold red]"
        )
        console.print(
            f"[yellow]{_('ui_failed_log_saved', path=f'[bold]{log_path}[/bold]')}[/yellow]\n"
        )
    else:
        console.print(f"\n[bold green]{_('ui_completed_success')}[/bold green]\n")


def run_test_mode(options):
    import sys
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from pydocstructurer import NativeRegexEngine, PdfParser

    console = Console()
    console.print(Panel(f"[bold green]{_('test_title')}[/bold green]", expand=False))

    pdf_path = options.TEST_FILE
    regex_path = options.REGEX_FILE

    console.print(f"[bold cyan]{_('test_pdf_file')}[/bold cyan] {pdf_path}")
    console.print(f"[bold cyan]{_('test_regex_file')}[/bold cyan] {regex_path}")

    # 1. Load Regex Engine
    try:
        engine = NativeRegexEngine.from_file(regex_path)
    except Exception as e:
        console.print(f"\n[bold red]{_('test_err_load_regex')} {e}[/bold red]")
        sys.exit(1)

    # 2. Extract First Page Text
    try:
        parser = PdfParser()
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(
                f"Arquivo PDF não encontrado: {pdf_path}"
                if get_lang() == Language.PT_BR
                else f"PDF file not found: {pdf_path}"
            )

        pages = [text for _, _, text in parser.process_file(pdf_path, pages_per_unit=1)]
        if not pages:
            raise ValueError(
                "O arquivo PDF não contém páginas."
                if get_lang() == Language.PT_BR
                else "The PDF file has no pages."
            )

        raw_text = pages[0]
        normalized_text = raw_text
    except Exception as e:
        console.print(f"\n[bold red]{_('test_err_read_pdf')} {e}[/bold red]")
        sys.exit(1)

    # Print a snippet of normalized text to help debug
    console.print(f"\n[bold yellow]{_('test_start_normalized_text')}[/bold yellow]")
    snippet = normalized_text[:500]
    console.print(snippet)
    if len(normalized_text) > 500:
        console.print("...")
    console.print(f"[bold yellow]{_('test_end_normalized_text')}[/bold yellow]\n")

    # 3. Match patterns
    results, matched_status = engine.parse_test(normalized_text)

    # 4. Render Table of Results
    table = Table(
        title=f"[bold green]{_('test_results_title')}[/bold green]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column(_("test_col_field"), style="cyan")
    table.add_column(_("test_col_status"), justify="center")
    table.add_column(_("test_col_value"), style="green")
    table.add_column(_("test_col_required"), justify="center")
    table.add_column(_("test_col_regex"), style="dim")

    has_missing_required = False
    missing_required_fields = []

    for key, entry in engine.patterns.items():
        matched = matched_status[key]
        required = entry["required"]
        val = results[key]
        regex_str = entry["regex_str"]

        status_str = (
            f"[green]{_('test_status_matched')}[/green]"
            if matched
            else f"[red]{_('test_status_not_found')}[/red]"
        )
        req_str = f"[bold red]{_('test_yes')}[/bold red]" if required else _("test_no")

        if required and not val:
            has_missing_required = True
            missing_required_fields.append(key)
            status_str = f"[bold red]{_('test_status_missing')}[/bold red]"

        val_display = val if val else f"[dim](default: '{entry['default']}')[/dim]"

        table.add_row(key, status_str, val_display, req_str, regex_str)

    console.print(table)

    if has_missing_required:
        console.print(
            f"\n[bold red]{_('test_missing_required', fields=', '.join(missing_required_fields))}[/bold red]"
        )
        sys.exit(1)
    else:
        console.print(f"\n[bold green]{_('test_all_matched')}[/bold green]")
        sys.exit(0)


def run_dump_mode(options):
    import os
    import sys
    from rich.console import Console
    from rich.panel import Panel
    from pydocstructurer.parser import ParserFactory
    from pydocstructurer.i18n import _

    console = Console()
    console.print(Panel(f"[bold green]{_('dump_title')}[/bold green]", expand=False))

    file_path = options.DUMP_FILE

    if not os.path.exists(file_path):
        console.print(f"\n[bold red]{_('err_dump_file_not_found', file_path=file_path)}[/bold red]")
        sys.exit(1)

    try:
        parser = ParserFactory.create(options.PARSER_TYPE)
    except Exception as e:
        console.print(f"\n[bold red]Error instantiating parser: {e}[/bold red]")
        sys.exit(1)

    try:
        has_units = False
        for unit_index, total_units, unit_text in parser.process_file(
            file_path, session=None, pages_per_unit=options.PAGES_PER_UNIT
        ):
            has_units = True
            console.print(
                f"\n[bold yellow]--- UNIT {unit_index} OF {total_units} ---[/bold yellow]\n"
            )
            console.print(unit_text)
            break

        if not has_units:
            console.print(f"\n[bold red]No text extracted from file.[/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]{_('err_dump_read', error=e)}[/bold red]")
        sys.exit(1)

    sys.exit(0)

