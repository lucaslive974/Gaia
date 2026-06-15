import os
import json
import pytest
from argparse import Namespace
from pyingestion.options import Options
from pyingestion.cli.cli_helper import CliHelper
from pyingestion.input_stream import InputStream
from pyingestion.transform_stream import TransformStream
from pyingestion.output_stream import OutputStream, SqliteOutputStream, CsvWriteStream


def test_config_pipeline_builder_parsing(temp_file_factory):
    # Prepare dummy regex rules file
    rules_data = {
        "title": {
            "regex": r"Title:\s*(.*)",
            "required": True
        }
    }
    rules_file = temp_file_factory("rules.json", rules_data, is_json=True)

    toml_content = f"""
    input_dir = "/toml/input"

    [input]
    type = "pdf"
    pages_per_unit = 2

    [transform]
    type = "regex"
    config_file = "{rules_file}"

    [output]
    type = "sqlite"
    db_path = "records.db"
    table_name = "pdf_records"
    """
    config_file = temp_file_factory("pipeline.toml", toml_content)

    args = Namespace(
        config=config_file,
        input_dir=None,
        output=None,
        resume=None,
        recursive=None,
        regex=None,
        test=None,
        dump=None,
        pages_per_unit=None,
        lang=None,
        type=None,
    )
    options = CliHelper.parse_and_build_options(args)

    input_stream, transform_stream, output_stream = CliHelper.build_pipeline(args, options)

    from pyingestion.input_stream import InputStream
    from pyingestion.transform_stream import TransformStream
    from pyingestion.output_stream import OutputStream

    assert isinstance(input_stream, InputStream)
    assert options.PAGES_PER_UNIT == 2
    assert transform_stream.config_file == rules_file
    assert isinstance(output_stream, SqliteOutputStream)
    assert output_stream.db_path == "records.db"
    assert output_stream.table_name == "pdf_records"
