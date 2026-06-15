from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from pyingestion.pyingestion import PyIngestion
from pyingestion.cli.main import cli


def test_main_execution_flow_to_ui(temp_file_factory):
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
            ],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "/dummy"


def test_main_execution_flow_to_dump():
    runner = CliRunner()
    with patch("pyingestion.cli.terminal_ui.run_dump_mode") as mock_run_dump:
        result = runner.invoke(cli, ["--dump", __file__, "pdf-input"])
        assert result.exit_code == 0
        mock_run_dump.assert_called_once()


def test_main_execution_flow_to_test(temp_file_factory):
    rules_file = temp_file_factory(
        "rules.json", {"invoice_title": {"regex": ".*"}}, is_json=True
    )
    runner = CliRunner()
    with patch("pyingestion.cli.terminal_ui.run_test_mode") as mock_run_test:
        result = runner.invoke(
            cli, ["--test", __file__, "pdf-input", "regex-transform", "-g", rules_file]
        )
        assert result.exit_code == 0
        mock_run_test.assert_called_once()
        args, kwargs = mock_run_test.call_args
        assert args[0] == __file__


@patch("pyingestion.pyingestion.os.path.exists")
def test_app_controller_validations_and_process(mock_exists):
    mock_exists.return_value = True

    controller = PyIngestion()
    input_stream = MagicMock()
    input_stream.read.return_value = iter([])
    transform_stream = MagicMock()
    output_stream = MagicMock()

    success = controller.process(
        source="/dummy/input",
        input_stream=input_stream,
        transform_stream=transform_stream,
        output_stream=output_stream,
    )
    assert success is True
    mock_exists.assert_any_call("/dummy/input")


@patch("pyingestion.cli.terminal_ui.Console")
@patch("pyingestion.cli.terminal_ui.Progress")
@patch("pyingestion.cli.terminal_ui.Live")
@patch("pyingestion.cli.terminal_ui.TerminalManager")
@patch("pyingestion.PyIngestion")
@patch("pyingestion.extraction_session.FileExtractionSession")
@patch("pyingestion.cli.terminal_ui.os.path.exists")
@patch("pyingestion.cli.terminal_ui.os.remove")
def test_cli_log_deletion(
    mock_remove,
    mock_exists,
    mock_session_store,
    mock_pyingestion,
    mock_terminal_manager,
    mock_live,
    mock_progress,
    mock_console,
):
    mock_exists.side_effect = lambda p: True if "gaia_errors.log" in p else False

    input_stream = MagicMock()
    transform_stream = MagicMock()
    output_stream = MagicMock()

    # Scenario 1: Resume is False -> Should remove gaia_errors.log if it exists
    from pyingestion.cli.terminal_ui import run_with_ui

    run_with_ui(
        source="/dummy/input",
        input_stream=input_stream,
        transform_stream=transform_stream,
        output_stream=output_stream,
        resume=False,
    )
    mock_remove.assert_called_once()

    # Scenario 2: Resume is True -> Should NOT remove gaia_errors.log
    mock_remove.reset_mock()
    mock_session_store_instance = MagicMock()
    mock_session_store_instance.load.return_value = {
        "processed_files": ["file1.pdf"],
        "successful_pages": 10,
        "failed_pages": 2,
        "total_pages": 12,
    }
    mock_session_store.return_value = mock_session_store_instance
    mock_session_store.load.return_value = mock_session_store_instance.load.return_value

    run_with_ui(
        source="/dummy/input",
        input_stream=input_stream,
        transform_stream=transform_stream,
        output_stream=output_stream,
        resume=True,
    )
    mock_remove.assert_not_called()


@patch("pyingestion.pyingestion.os.path.exists")
def test_gaia_process_with_direct_file(mock_exists):
    mock_exists.return_value = True

    input_stream = MagicMock()
    input_stream.read.return_value = iter(["page text"])
    input_stream.current_unit_index = 1
    input_stream.total_units = 1

    transform_stream = MagicMock()
    transform_stream.transform.return_value = {"field": "value"}
    output_stream = MagicMock()

    controller = PyIngestion()
    session = MagicMock()
    session.is_cancelled = False

    success = controller.process(
        source="/dummy/input/file.pdf",
        input_stream=input_stream,
        transform_stream=transform_stream,
        output_stream=output_stream,
        session=session,
    )
    assert success is True
    input_stream.read.assert_called_once_with("/dummy/input/file.pdf", session=session)
    transform_stream.transform.assert_called_once_with("page text")
    output_stream.write.assert_called_once_with({"field": "value"})


def test_default_output_stream_generator():
    from pyingestion.output_stream import DefaultOutputStream

    stream = DefaultOutputStream()
    stream.write({"field": "val1"})
    stream.write({"field": "val2"})

    # Test that iterating over it returns a generator yielding items
    results = list(stream)
    assert results == [{"field": "val1"}, {"field": "val2"}]
