from unittest.mock import patch

from click.testing import CliRunner

from pyingestion.cli.main import cli
from pyingestion.output_stream import CsvWriteStream, SqliteOutputStream


def test_click_cli_csv_mapping(temp_file_factory):
    rules_file = temp_file_factory(
        "rules.json", {"invoice_title": {"regex": ".*"}}, is_json=True
    )
    runner = CliRunner()
    with patch("pyingestion.cli.terminal_ui.run_with_ui") as mock_run:
        result = runner.invoke(
            cli,
            [
                "--source",
                "/dummy",
                "pdf-input",
                "regex-transform",
                "-g",
                rules_file,
                "csv-output",
                "-o",
                "custom_output.csv",
            ],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "/dummy"
        assert isinstance(kwargs["output_stream"], CsvWriteStream)
        assert kwargs["output_stream"]._path == "custom_output.csv"


def test_click_cli_sqlite_mapping(temp_file_factory):
    rules_file = temp_file_factory(
        "rules.json", {"invoice_title": {"regex": ".*"}}, is_json=True
    )
    runner = CliRunner()
    with patch("pyingestion.cli.terminal_ui.run_with_ui") as mock_run:
        result = runner.invoke(
            cli,
            [
                "--source",
                "/dummy",
                "pdf-input",
                "regex-transform",
                "-g",
                rules_file,
                "sqlite-output",
                "--db",
                "custom.db",
                "--table",
                "my_table",
            ],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "/dummy"
        assert isinstance(kwargs["output_stream"], SqliteOutputStream)
        assert kwargs["output_stream"].db_path == "custom.db"
        assert kwargs["output_stream"].table_name == "my_table"
