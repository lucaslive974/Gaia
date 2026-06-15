import os
import pytest
from argparse import Namespace
from pyingestion.options import Options
from pyingestion.cli.cli_helper import CliHelper
from pyingestion.output_stream import CsvWriteStream, SqliteOutputStream, MysqlOutputStream


def test_cli_to_mapping_csv(temp_file_factory):
    rules_file = temp_file_factory("rules.json", {"f": {"regex": ".*"}}, is_json=True)
    args = Namespace(
        config=None,
        input_dir="/dummy",
        output="custom_output.csv",
        resume=None,
        recursive=None,
        regex=rules_file,
        test=None,
        dump=None,
        pages_per_unit=None,
        lang=None,
        type=None,
        to="csv"
    )
    options = CliHelper.parse_and_build_options(args)
    assert options.TO == "csv"

    _, _, output_stream = CliHelper.build_pipeline(args, options)
    assert isinstance(output_stream, CsvWriteStream)
    assert output_stream._path == "custom_output.csv"


def test_cli_to_mapping_sqlite(temp_file_factory):
    rules_file = temp_file_factory("rules.json", {"f": {"regex": ".*"}}, is_json=True)
    args = Namespace(
        config=None,
        input_dir="/dummy",
        output="custom_output.csv",
        resume=None,
        recursive=None,
        regex=rules_file,
        test=None,
        dump=None,
        pages_per_unit=None,
        lang=None,
        type=None,
        to="sqlite"
    )
    options = CliHelper.parse_and_build_options(args)
    assert options.TO == "sqlite"

    _, _, output_stream = CliHelper.build_pipeline(args, options)
    assert isinstance(output_stream, SqliteOutputStream)
    assert output_stream.db_path == "custom_output.db"
