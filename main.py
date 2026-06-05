import argparse
import os
import sys
import time
from typing import Any
from config.settings import settings
from core.ocr_parser import DefaultOcrParser
from core.observer import ExtractionObserver
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table


class ConsoleObserver(ExtractionObserver):
    def __init__(self, console: Console, progress: Progress):
        self.console = console
        self.progress = progress
        self.total_files_task = None
        self.current_file_task = None
        self.is_cancelled = False

    def on_start(self, total_files: int):
        self.console.print(f"[bold green]▶️ Iniciando processamento de {total_files} arquivo(s)...[/bold green]")
        self.total_files_task = self.progress.add_task("[cyan]Arquivos", total=total_files)

    def on_file_start(self, file_index: int, file_path: str, estimated_hours: float):
        file_name = os.path.basename(file_path)
        self.console.print(f"\n[bold blue]📂 [{file_index}] Processando:[/bold blue] {file_name} [dim](Est. restante: {estimated_hours:.2f}h)[/dim]")
        
        # Reset/add task for pages in the current file
        if self.current_file_task is not None:
            self.progress.remove_task(self.current_file_task)
        self.current_file_task = self.progress.add_task(f"[magenta]  Páginas ({file_name})", total=0)

    def on_page_start(self, page_index: int, total_pages: int):
        if self.current_file_task is not None:
            self.progress.update(self.current_file_task, total=total_pages)

    def on_page_processed(
        self,
        success: bool,
        extracted_pages: int,
        error_pages: int,
        page_index: int,
        total_pages: int,
        native_pages: int,
        ocr_pages: int,
        method: str
    ):
        if self.current_file_task is not None:
            self.progress.update(self.current_file_task, completed=page_index)
        method_str = "[cyan]Nativo[/cyan]" if method == "native" else "[yellow]OCR Tesseract[/yellow]"
        if success:
            self.console.print(f"  ✔️ Página {page_index}/{total_pages} extraída ({method_str}).")
        else:
            self.console.print(f"  ❌ Falha na extração da página {page_index}/{total_pages}.")

    def on_file_complete(self, file_index: int, progress_percent: float):
        self.console.print(f"[bold green]✅ Arquivo {file_index} concluído![/bold green]")
        if self.total_files_task is not None:
            self.progress.update(self.total_files_task, completed=file_index)

    def on_complete(self, successful_pages: int, total_pages: int):
        # Clean up pages task
        if self.current_file_task is not None:
            self.progress.remove_task(self.current_file_task)

    def on_error(self, error_message: str):
        self.console.print(f"[bold red]🚨 ERRO: {error_message}[/bold red]")


def print_summary_dashboard(
    console: Console,
    total_files: int,
    total_pages: int,
    successful_pages: int,
    native_pages: int,
    ocr_pages: int,
    elapsed_time: float
):
    table = Table(title="[bold green]📊 Resumo da Extração[/bold green]", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green", justify="right")

    table.add_row("Arquivos Processados", str(total_files))
    table.add_row("Total de Páginas", str(total_pages))
    table.add_row("Páginas Nativas (Leve/Rápido)", f"[blue]{native_pages}[/blue]")
    table.add_row("Páginas OCR Tesseract (Pesado)", f"[yellow]{ocr_pages}[/yellow]")
    table.add_row("Falhas de Extração", f"[red]{total_pages - successful_pages}[/red]")
    table.add_row("Tempo Total Decorrido", f"{elapsed_time:.2f} segundos")
    
    console.print("\n")
    console.print(table)
    console.print("\n[bold green]🎉 Processamento concluído com sucesso![/bold green]")


def main():
    parser = argparse.ArgumentParser(
        description="Gaia/Atlas PDF Extractor - Ferramenta CLI de extração inteligente de dados de PDFs."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="Caminho do diretório contendo os arquivos PDF a serem processados."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=settings["OUTPUT_CSV"],
        help=f"Caminho do arquivo CSV de saída (Padrão: {settings['OUTPUT_CSV']})."
    )
    parser.add_argument(
        "-t", "--traineddata",
        type=str,
        default=settings["TRAINED_DATA_DIR"],
        help=f"Caminho da pasta traineddata do Tesseract (Padrão: {settings['TRAINED_DATA_DIR']})."
    )
    
    args = parser.parse_args()

    console = Console()

    # Validações iniciais
    if not os.path.exists(args.input_dir):
        console.print(f"[bold red]Erro:[/bold red] O diretório de entrada '{args.input_dir}' não existe.")
        sys.exit(1)
        
    if not os.path.isdir(args.input_dir):
        console.print(f"[bold red]Erro:[/bold red] O caminho de entrada '{args.input_dir}' não é um diretório.")
        sys.exit(1)

    # Configura o diretório de dados treinados e de saída nos settings
    settings["BASE_PATH"] = os.path.abspath(args.input_dir)
    settings["OUTPUT_CSV"] = os.path.abspath(args.output)
    settings["TRAINED_DATA_DIR"] = os.path.abspath(args.traineddata)

    # Garante que a pasta de destino do CSV exista
    output_dir = os.path.dirname(settings["OUTPUT_CSV"])
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Cria o parser orquestrador com a configuração de saída
    from core.extractor import FallbackPdfExtractor
    from core.csv_writer import DefaultCsvWriter
    
    csv_writer = DefaultCsvWriter()
    extractor = FallbackPdfExtractor()
    ocr_parser = DefaultOcrParser(extractor=extractor, csv_writer=csv_writer)

    start_time = time.perf_counter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        observer = ConsoleObserver(console, progress)
        try:
            ocr_parser.process(settings["BASE_PATH"], observer)
        except Exception as e:
            console.print(f"[bold red]🚨 Erro crítico durante o processamento: {e}[/bold red]")
            sys.exit(1)

    elapsed_time = time.perf_counter() - start_time

    # Exibe o dashboard de resumo
    total_pages = ocr_parser._total_pages
    successful_pages = ocr_parser._successful_pages
    native_pages = ocr_parser._native_pages
    ocr_pages = ocr_parser._ocr_pages
    
    # Lista arquivos PDF no diretório para contar
    total_files = len([f for f in os.listdir(settings["BASE_PATH"]) if f.lower().endswith(".pdf")])

    print_summary_dashboard(
        console=console,
        total_files=total_files,
        total_pages=total_pages,
        successful_pages=successful_pages,
        native_pages=native_pages,
        ocr_pages=ocr_pages,
        elapsed_time=elapsed_time
    )


if __name__ == "__main__":
    main()
