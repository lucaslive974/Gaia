import click
import os
import sys
from pyingestion.i18n import _, set_lang, parse_lang_from_argv
from pyingestion.input_stream import InputStream
from pyingestion.transform_stream import TransformStream
from pyingestion.output_stream import OutputStream


def load_config_file(file_path: str) -> dict:
    import json
    import tomllib
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".toml":
            with open(file_path, "rb") as f:
                return tomllib.load(f)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Error loading config file: {e}")


def build_input_stream_from_config(config_data: dict) -> InputStream:
    from pyingestion.input_stream import InputStreamFactory
    input_section = config_data.get("input")
    if isinstance(input_section, dict):
        input_type = input_section.get("type", "pdf")
        pages_per_unit = int(input_section.get("pages_per_unit", 1))
        recursive = bool(input_section.get("recursive", False))
        return InputStreamFactory.create(input_type, pages_per_unit, recursive)
    return InputStreamFactory.create("pdf")


def build_transform_stream_from_config(config_data: dict) -> TransformStream:
    from pyingestion.transform_stream import NativeRegexEngine, ChainedTransformStream
    transform_data = config_data.get("transform")
    if not transform_data:
        regex_path = config_data.get("regex")
        if not regex_path:
            raise click.UsageError("Transform section or 'regex' path is required in config.")
        return NativeRegexEngine.from_file(regex_path)

    def instantiate_transform(item: dict) -> TransformStream:
        t_type = item.get("type")
        if t_type == "regex":
            rules_file = item.get("config_file") or item.get("rules_file")
            if not rules_file:
                raise click.UsageError("Transform of type 'regex' requires 'config_file' or 'rules_file'.")
            return NativeRegexEngine.from_file(rules_file)
        else:
            raise click.UsageError(f"Unknown transform type: {t_type}")

    if isinstance(transform_data, list):
        transforms = [instantiate_transform(item) for item in transform_data]
        if len(transforms) == 1:
            return transforms[0]
        return ChainedTransformStream(transforms)
    elif isinstance(transform_data, dict):
        return instantiate_transform(transform_data)

    raise click.UsageError("The 'transform' section must be a dictionary or a list of dictionaries.")


def build_output_stream_from_config(config_data: dict) -> OutputStream:
    from pyingestion.output_stream import (
        CsvWriteStream,
        SqliteOutputStream,
        MysqlOutputStream,
        MultiOutputStream,
    )
    output_data = config_data.get("output")
    if not output_data:
        to_dest = config_data.get("to", "csv")
        out_path = config_data.get("output", "output.csv")
        if to_dest == "sqlite":
            if out_path.endswith(".csv"):
                out_path = out_path[:-4] + ".db"
            return SqliteOutputStream(out_path)
        elif to_dest == "mysql":
            connection_uri = os.environ.get("DATABASE_URL")
            if not connection_uri:
                raise click.UsageError("Environment variable 'DATABASE_URL' is required for MySQL output.")
            return MysqlOutputStream(connection_uri=connection_uri)
        else:
            return CsvWriteStream(out_path)

    def instantiate_output(item: dict) -> OutputStream:
        out_type = item.get("type")
        if out_type == "csv":
            out_path = item.get("path") or item.get("output") or "output.csv"
            return CsvWriteStream(out_path)
        elif out_type == "sqlite":
            db_path = item.get("db_path") or item.get("path") or "records.db"
            table_name = item.get("table_name") or item.get("table") or "extracted_data"
            return SqliteOutputStream(db_path, table_name)
        elif out_type == "mysql":
            conn_uri = item.get("connection_uri") or item.get("connection") or os.environ.get("DATABASE_URL")
            if not conn_uri:
                raise click.UsageError("MySQL output requires 'connection_uri' or env var 'DATABASE_URL'.")
            table_name = item.get("table_name") or item.get("table") or "extracted_data"
            return MysqlOutputStream(connection_uri=conn_uri, table_name=table_name)
        else:
            raise click.UsageError(f"Unknown output type: {out_type}")

    if isinstance(output_data, list):
        outputs = [instantiate_output(item) for item in output_data]
        if len(outputs) == 1:
            return outputs[0]
        return MultiOutputStream(outputs)
    elif isinstance(output_data, dict):
        return instantiate_output(output_data)

    raise click.UsageError("The 'output' section must be a dictionary or a list of dictionaries.")


@click.group(chain=True, invoke_without_command=True)
@click.option("--source", "-s", type=click.Path(), help="Input source path (file or directory).")
@click.option("--resume", is_flag=True, help="Resume execution using checkpoint store.")
@click.option("--test", "-t", type=click.Path(exists=True), help="Run in test mode on a specific file.")
@click.option("--dump", "-d", type=click.Path(exists=True), help="Run in dump mode on a specific file.")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file (JSON or TOML).")
@click.option("--lang", "-l", type=click.Choice(["en", "pt"]), help="Language for the interface.")
@click.version_option(version="0.5.2b1", package_name="pyingestion")
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
@click.option("--pages-per-unit", default=1, type=int, help="Number of pages per processing unit.")
@click.option("--recursive", is_flag=True, help="Scan directories recursively.")
@click.pass_context
def pdf_input(ctx, pages_per_unit, recursive):
    from pyingestion.input_streams import PdfInputStream
    ctx.obj["input_stream"] = PdfInputStream(pages_per_unit=pages_per_unit, recursive=recursive)


@cli.command("docx-input")
@click.option("--pages-per-unit", default=1, type=int, help="Number of pages per processing unit.")
@click.option("--recursive", is_flag=True, help="Scan directories recursively.")
@click.pass_context
def docx_input(ctx, pages_per_unit, recursive):
    from pyingestion.input_streams import DocxInputStream
    ctx.obj["input_stream"] = DocxInputStream(pages_per_unit=pages_per_unit, recursive=recursive)


@cli.command("ocr-input")
@click.option("--pages-per-unit", default=1, type=int, help="Number of pages per processing unit.")
@click.option("--recursive", is_flag=True, help="Scan directories recursively.")
@click.pass_context
def ocr_input(ctx, pages_per_unit, recursive):
    from pyingestion.input_streams import OcrInputStream
    ctx.obj["input_stream"] = OcrInputStream(pages_per_unit=pages_per_unit, recursive=recursive)


@cli.command("regex-transform")
@click.option("-g", "--regex", "--config-file", required=True, help="Path to regex rules JSON/TOML file.")
@click.pass_context
def regex_transform(ctx, regex):
    from pyingestion.transform_stream import NativeRegexEngine
    ctx.obj["transform_stream"] = NativeRegexEngine.from_file(regex)


@cli.command("csv-output")
@click.option("-o", "--output", "--path", default="output.csv", help="Path to output CSV file.")
@click.pass_context
def csv_output(ctx, output):
    from pyingestion.output_stream import CsvWriteStream
    ctx.obj["output_stream"] = CsvWriteStream(output)


@cli.command("sqlite-output")
@click.option("--db", "--db-path", "--path", required=True, help="Path to SQLite database file.")
@click.option("--table", "--table-name", default="extracted_data", help="Table name in database.")
@click.pass_context
def sqlite_output(ctx, db, table):
    from pyingestion.output_stream import SqliteOutputStream
    ctx.obj["output_stream"] = SqliteOutputStream(db, table)


@cli.command("mysql-output")
@click.option("--connection", "--connection-uri", help="MySQL connection URI.")
@click.option("--table", "--table-name", default="extracted_data", help="Table name in database.")
@click.pass_context
def mysql_output(ctx, connection, table):
    from pyingestion.output_stream import MysqlOutputStream
    conn = connection or os.environ.get("DATABASE_URL")
    if not conn:
        raise click.UsageError("MySQL output requires --connection or environment variable DATABASE_URL.")
    ctx.obj["output_stream"] = MysqlOutputStream(connection_uri=conn, table_name=table)


@cli.result_callback()
@click.pass_context
def process_pipeline(ctx, processors, **kwargs):
    source = ctx.obj.get("source")
    resume = ctx.obj.get("resume")
    test_file = ctx.obj.get("test")
    dump_file = ctx.obj.get("dump")
    config_path = ctx.obj.get("config")

    config_data = {}
    if config_path:
        config_data = load_config_file(config_path)
        if "config" in config_data and isinstance(config_data["config"], dict):
            config_data = config_data["config"]

    if not source:
        source = config_data.get("input_dir") or config_data.get("source")

    # Resolve input_stream
    input_stream = ctx.obj.get("input_stream")
    if not input_stream and config_path:
        input_stream = build_input_stream_from_config(config_data)
    if not input_stream and (test_file or dump_file):
        from pyingestion.input_streams import PdfInputStream
        ext = os.path.splitext(test_file or dump_file)[1].lower()
        if ext == ".docx":
            from pyingestion.input_streams import DocxInputStream
            input_stream = DocxInputStream()
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            from pyingestion.input_streams import OcrInputStream
            input_stream = OcrInputStream()
        else:
            input_stream = PdfInputStream()

    # Resolve transform_stream
    transform_stream = ctx.obj.get("transform_stream")
    if not transform_stream and config_path:
        transform_stream = build_transform_stream_from_config(config_data)

    # Resolve output_stream
    output_stream = ctx.obj.get("output_stream")
    if not output_stream and config_path:
        output_stream = build_output_stream_from_config(config_data)
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
                from pyingestion.session_store import FileSessionStore
                state = FileSessionStore().load(test_file)
                if state:
                    regex_path = state.get("config_file") or state.get("regex_file")
                    if regex_path:
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
            from pyingestion.session_store import FileSessionStore
            cwd_state = os.path.join(os.getcwd(), ".gaia_resume.json")
            if os.path.exists(cwd_state):
                try:
                    with open(cwd_state, "r", encoding="utf-8") as f:
                        import json
                        data = json.load(f)
                        if data.get("input_dir"):
                            source = data.get("input_dir")
                except Exception:
                    pass
        if not source:
            raise click.UsageError("Source path is required.")

    if not transform_stream:
        if resume:
            from pyingestion.session_store import FileSessionStore
            state = FileSessionStore().load(source)
            if state:
                regex_path = state.get("config_file") or state.get("regex_file")
                if regex_path:
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


def main():
    cli()


if __name__ == "__main__":
    main()
