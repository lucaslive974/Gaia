import os
from click.testing import CliRunner
from unittest.mock import patch
from pyingestion.cli.main import cli
from pyingestion.input_stream import InputStream
from pyingestion.transform_stream import TransformStream
from pyingestion.output_stream import SqliteOutputStream


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

    runner = CliRunner()
    with patch("pyingestion.cli.terminal_ui.run_with_ui") as mock_run:
        result = runner.invoke(cli, [
            "--config", config_file
        ])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "/toml/input"
        assert isinstance(kwargs["input_stream"], InputStream)
        assert kwargs["input_stream"].pages_per_unit == 2
        assert kwargs["transform_stream"].config_file == rules_file
        assert isinstance(kwargs["output_stream"], SqliteOutputStream)
        assert kwargs["output_stream"].db_path == "records.db"
        assert kwargs["output_stream"].table_name == "pdf_records"
