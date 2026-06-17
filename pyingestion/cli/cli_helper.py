import click
import os
from typing import cast
from pyingestion.i18n import set_lang

from pyingestion.cli.builder import (
    load_config_file,
    build_input_stream_from_config,
    build_transform_stream_from_config,
    build_output_stream_from_config,
)


@click.group(chain=True, invoke_without_command=True)
@click.option(
    "--source", "-s", type=click.Path(), help="Input source path (file or directory)."
)
@click.option("--resume", is_flag=True, help="Resume execution using checkpoint store.")
@click.option(
    "--test",
    "-t",
    type=click.Path(exists=True),
    help="Run in test mode on a specific file.",
)
@click.option(
    "--dump",
    "-d",
    type=click.Path(exists=True),
    help="Run in dump mode on a specific file.",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to config file (JSON or TOML).",
)
@click.option(
    "--lang", "-l", type=click.Choice(["en", "pt"]), help="Language for the interface."
)
@click.version_option(version="0.5.3b1", package_name="pyingestion")
@click.pass_context
def cli(ctx, source, resume, test, dump, config, lang):
    """
    PyIngestion Command Line Tool
    """
    ctx.ensure_object(dict)
    ctx.obj["source"] = source
    ctx.obj["resume"] = resume
    ctx.obj["test"] = test
    ctx.obj["dump"] = dump
    ctx.obj["config"] = config

    if lang:
        set_lang(lang)


@cli.command("pdf-input")
@click.option(
    "--pages-per-unit", default=1, type=int, help="Number of pages per processing unit."
)
@click.option("--recursive", is_flag=True, help="Scan directories recursively.")
@click.pass_context
def pdf_input(ctx, pages_per_unit, recursive):
    from pyingestion.input_streams import PdfInputStream

    ctx.obj["input_stream"] = PdfInputStream(
        pages_per_unit=pages_per_unit, recursive=recursive
    )


@cli.command("docx-input")
@click.option(
    "--pages-per-unit", default=1, type=int, help="Number of pages per processing unit."
)
@click.option("--recursive", is_flag=True, help="Scan directories recursively.")
@click.pass_context
def docx_input(ctx, pages_per_unit, recursive):
    from pyingestion.input_streams import DocxInputStream

    ctx.obj["input_stream"] = DocxInputStream(
        pages_per_unit=pages_per_unit, recursive=recursive
    )


@cli.command("ocr-input")
@click.option(
    "--pages-per-unit", default=1, type=int, help="Number of pages per processing unit."
)
@click.option("--recursive", is_flag=True, help="Scan directories recursively.")
@click.pass_context
def ocr_input(ctx, pages_per_unit, recursive):
    from pyingestion.input_streams import OcrInputStream

    ctx.obj["input_stream"] = OcrInputStream(
        pages_per_unit=pages_per_unit, recursive=recursive
    )


@cli.command("regex-transform")
@click.option(
    "-g",
    "--regex",
    "--config-file",
    required=True,
    help="Path to regex rules JSON/TOML file.",
)
@click.pass_context
def regex_transform(ctx, regex):
    from pyingestion.transform_stream import NativeRegexEngine

    ctx.obj["transform_stream"] = NativeRegexEngine.from_file(regex)


@cli.command("embed-transform")
@click.option("--chunk-size", default=500, type=int, help="Size of each text chunk.")
@click.option("--chunk-overlap", default=100, type=int, help="Overlap between chunks.")
@click.option("--device", default=None, type=str, help="Device to run embedding model on (e.g., cpu, cuda).")
@click.pass_context
def embed_transform(ctx, chunk_size, chunk_overlap, device):
    from pyingestion.rag_streams import ChunkerTransformStream

    ctx.obj["transform_stream"] = ChunkerTransformStream(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, device=device
    )


@cli.command("csv-output")
@click.option(
    "-o", "--output", "--path", default="output.csv", help="Path to output CSV file."
)
@click.pass_context
def csv_output(ctx, output):
    from pyingestion.output_stream import CsvWriteStream

    ctx.obj["output_stream"] = CsvWriteStream(output)


@cli.command("sqlite-output")
@click.option(
    "--db", "--db-path", "--path", required=True, help="Path to SQLite database file."
)
@click.option(
    "--table", "--table-name", default="extracted_data", help="Table name in database."
)
@click.pass_context
def sqlite_output(ctx, db, table):
    from pyingestion.output_stream import SqliteOutputStream

    ctx.obj["output_stream"] = SqliteOutputStream(db, table)


@cli.command("sqlite-vector-output")
@click.option(
    "--db", "--db-path", "--path", default="vector_store.db", help="Path to SQLite database file."
)
@click.option(
    "--table", "--table-name", default="embeddings", help="Table name in database."
)
@click.pass_context
def sqlite_vector_output(ctx, db, table):
    from pyingestion.rag_streams import SqliteVectorOutputStream

    ctx.obj["output_stream"] = SqliteVectorOutputStream(db_path=db, table_name=table)


@cli.command("mysql-output")
@click.option("--connection", "--connection-uri", help="MySQL connection URI.")
@click.option(
    "--table", "--table-name", default="extracted_data", help="Table name in database."
)
@click.pass_context
def mysql_output(ctx, connection, table):
    from pyingestion.output_stream import MysqlOutputStream

    conn = connection or os.environ.get("DATABASE_URL")
    if not conn:
        raise click.UsageError(
            "MySQL output requires --connection or environment variable DATABASE_URL."
        )
    ctx.obj["output_stream"] = MysqlOutputStream(connection_uri=conn, table_name=table)


@cli.result_callback()
@click.pass_context
def process_pipeline(ctx, _processors, **_kwargs):
    source = ctx.obj.get("source")
    resume = ctx.obj.get("resume")
    test_file = ctx.obj.get("test")
    dump_file = ctx.obj.get("dump")
    config_path = ctx.obj.get("config")

    config_obj = None
    if config_path:
        config_data = load_config_file(config_path)
        if "config" in config_data and isinstance(config_data["config"], dict):
            config_data = config_data["config"]
        from pyingestion.config_models import PipelineConfig

        try:
            config_obj = PipelineConfig.model_validate(config_data)
        except Exception as e:
            raise click.ClickException(f"Configuration validation error: {e}")

    if not source:
        if config_obj:
            source = config_obj.input_dir or config_obj.source

    # Resolve input_stream
    input_stream = ctx.obj.get("input_stream")
    if not input_stream and config_path:
        input_stream = build_input_stream_from_config(config_obj)
    if not input_stream and (test_file or dump_file):
        from pyingestion.input_streams import InputStreamFactory

        input_stream = InputStreamFactory.from_file_path(str(test_file or dump_file))

    # Resolve transform_stream
    transform_stream = ctx.obj.get("transform_stream")
    if not transform_stream and config_path:
        transform_stream = build_transform_stream_from_config(config_obj)

    # Resolve output_stream
    output_stream = ctx.obj.get("output_stream")
    if not output_stream and config_path:
        output_stream = build_output_stream_from_config(config_obj)
    if not output_stream:
        from pyingestion.output_stream import CsvWriteStream

        output_stream = CsvWriteStream()

    # 1. Run Dump Mode
    if dump_file:
        from pyingestion.cli.terminal_ui import run_dump_mode

        if not input_stream:
            raise click.UsageError("Dump mode requires an input stream type.")
        run_dump_mode(dump_file, input_stream)
        return

    # 2. Run Test Mode
    if test_file:
        if not transform_stream:
            if resume:
                from pyingestion.extraction_session import FileExtractionSession

                state = FileExtractionSession.load(str(test_file))
                if state:
                    regex_path = state.get("config_file") or state.get("regex_file")
                    if isinstance(regex_path, str):
                        from pyingestion.transform_stream import NativeRegexEngine

                        transform_stream = NativeRegexEngine.from_file(regex_path)
            if not transform_stream:
                raise click.UsageError("Test mode requires a transform stream.")
        from pyingestion.cli.terminal_ui import run_test_mode

        run_test_mode(test_file, transform_stream, input_stream=input_stream)
        return

    # 3. Regular Execution (UI Mode)
    if not source:
        if resume:
            from pyingestion.extraction_session import FileExtractionSession

            cwd_state = os.path.join(os.getcwd(), ".gaia_resume.json")
            if os.path.exists(cwd_state):
                try:
                    with open(cwd_state, "r", encoding="utf-8") as f:
                        import json

                        data = cast(dict[str, object], json.load(f))
                        if data.get("input_dir"):
                            source = str(data.get("input_dir"))
                except Exception:
                    pass
        if not source:
            raise click.UsageError("Source path is required.")

    if not transform_stream:
        if resume:
            from pyingestion.extraction_session import FileExtractionSession

            state = FileExtractionSession.load(str(source))
            if state:
                regex_path = state.get("config_file") or state.get("regex_file")
                if isinstance(regex_path, str):
                    from pyingestion.transform_stream import NativeRegexEngine

                    transform_stream = NativeRegexEngine.from_file(regex_path)
        if not transform_stream:
            raise click.UsageError("Transform stream is required.")

    if not input_stream:
        from pyingestion.input_streams import PdfInputStream

        input_stream = PdfInputStream()

    from pyingestion.cli.terminal_ui import run_with_ui

    run_with_ui(
        source,
        input_stream=input_stream,
        transform_stream=transform_stream,
        output_stream=output_stream,
        resume=resume,
    )
