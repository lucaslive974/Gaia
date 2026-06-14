import pytest
from unittest.mock import patch, MagicMock

from pyingestion.main import main
from pyingestion.pyingestion import PyIngestion as Gaia
from pyingestion.options import Options


class TestCliMainOrchestration:
    @patch("sys.argv", ["main.py", "--lang", "en"])
    @patch("pyingestion.main.run_with_ui")
    @patch("pyingestion.main.CliHelper")
    @patch("pyingestion.main.parse_lang_from_argv")
    @patch("pyingestion.main.set_lang")
    def test_main_execution_flow_to_ui(
        self, mock_set_lang, mock_parse_lang, mock_cli_helper, mock_run_with_ui
    ):
        mock_parse_lang.return_value = "en"
        mock_parser = MagicMock()
        mock_cli_helper.get_argument_parser.return_value = mock_parser

        mock_options = Options()
        mock_options.DUMP_FILE = None
        mock_options.TEST_FILE = None
        mock_cli_helper.parse_and_build_options.return_value = mock_options

        mock_transform = MagicMock()
        mock_cli_helper.build_transform.return_value = mock_transform

        main()

        mock_parse_lang.assert_called_once_with(["main.py", "--lang", "en"])
        mock_set_lang.assert_called_once_with("en")
        mock_cli_helper.get_argument_parser.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_cli_helper.parse_and_build_options.assert_called_once_with(
            mock_parser.parse_args.return_value
        )
        mock_cli_helper.build_transform.assert_called_once_with(
            mock_parser.parse_args.return_value, mock_options
        )
        mock_run_with_ui.assert_called_once_with(mock_options, mock_transform)

    @patch("pyingestion.cli.terminal_ui.run_dump_mode")
    @patch("pyingestion.main.CliHelper")
    def test_main_execution_flow_to_dump(self, mock_cli_helper, mock_run_dump_mode):
        mock_parser = MagicMock()
        mock_cli_helper.get_argument_parser.return_value = mock_parser

        mock_options = Options()
        mock_options.DUMP_FILE = "/path/to/dump.pdf"
        mock_options.TEST_FILE = None
        mock_cli_helper.parse_and_build_options.return_value = mock_options

        main()

        mock_run_dump_mode.assert_called_once_with(mock_options)

    @patch("pyingestion.cli.terminal_ui.run_test_mode")
    @patch("pyingestion.main.CliHelper")
    def test_main_execution_flow_to_test(self, mock_cli_helper, mock_run_test_mode):
        mock_parser = MagicMock()
        mock_cli_helper.get_argument_parser.return_value = mock_parser

        mock_options = Options()
        mock_options.DUMP_FILE = None
        mock_options.TEST_FILE = "/path/to/test.pdf"
        mock_cli_helper.parse_and_build_options.return_value = mock_options

        mock_transform = MagicMock()
        mock_cli_helper.build_transform.return_value = mock_transform

        main()

        mock_run_test_mode.assert_called_once_with(mock_options, mock_transform)

    @patch("pyingestion.main.CliHelper")
    def test_main_handles_value_error(self, mock_cli_helper):
        mock_parser = MagicMock()
        mock_parser.error.side_effect = SystemExit(2)
        mock_cli_helper.get_argument_parser.return_value = mock_parser

        mock_cli_helper.parse_and_build_options.side_effect = ValueError(
            "Some error message"
        )

        with pytest.raises(SystemExit):
            main()

        mock_parser.error.assert_called_once_with("Some error message")


@patch("pyingestion.pyingestion.os.path.exists")
@patch("pyingestion.pyingestion.os.path.isdir")
@patch("pyingestion.pyingestion.DefaultOutputStream")
def test_app_controller_validations_and_run(
    mock_output_stream, mock_isdir, mock_exists
):
    mock_exists.return_value = True
    mock_isdir.return_value = True

    options = Options()
    options.BASE_PATH = "/dummy/input"
    options.OUTPUT_CSV = "/dummy/output.csv"
    options.RESUME = True

    mock_observer = MagicMock()
    mock_transform = MagicMock()
    mock_transform.config_file = "/dummy/regex.json"
    controller = Gaia(options, transform_stream=mock_transform, observer=mock_observer)

    # mock os.listdir to return empty list so it finishes quickly
    with patch("pyingestion.pyingestion.os.listdir", return_value=[]):
        success = controller.run(options)

    assert success is True
    mock_exists.assert_any_call("/dummy/input")
    mock_isdir.assert_any_call("/dummy/input")


@patch("pyingestion.pyingestion.os.path.exists")
@patch("pyingestion.pyingestion.os.path.isdir")
@patch("pyingestion.pyingestion.os.remove")
def test_app_controller_log_deletion(
    mock_remove, mock_isdir, mock_exists
):
    # Scenario 1: Resume is False -> Should remove gaia_errors.log if it exists
    mock_exists.side_effect = lambda p: (
        True if "gaia_errors.log" in p or p == "/dummy/input" else False
    )
    mock_isdir.return_value = True

    options = Options()
    options.BASE_PATH = "/dummy/input"
    options.OUTPUT_CSV = "/dummy/output.csv"
    options.RESUME = False

    mock_observer = MagicMock()
    mock_transform = MagicMock()
    controller = Gaia(options, transform_stream=mock_transform, observer=mock_observer)

    with patch("pyingestion.pyingestion.os.listdir", return_value=[]):
        controller.run(options)
    mock_remove.assert_called_once()

    # Scenario 2: Resume is True -> Should NOT remove gaia_errors.log
    mock_remove.reset_mock()
    options.RESUME = True
    with patch("pyingestion.pyingestion.os.listdir", return_value=[]):
        controller.run(options)
    mock_remove.assert_not_called()


@patch("pyingestion.pyingestion.os.makedirs")
@patch("pyingestion.pyingestion.os.path.exists")
@patch("pyingestion.pyingestion.os.path.isfile")
@patch("pyingestion.pyingestion.os.path.isdir")
@patch("pyingestion.parsers.PdfParser")
@patch("pyingestion.pyingestion.DefaultOutputStream")
def test_gaia_run_with_direct_file(
    mock_output_stream,
    mock_parser_class,
    mock_isdir,
    mock_isfile,
    mock_exists,
    mock_makedirs,
):
    mock_exists.return_value = True
    mock_isdir.return_value = False
    mock_isfile.return_value = True

    mock_parser_instance = MagicMock()
    mock_parser_class.return_value = mock_parser_instance
    mock_parser_instance.process_file.return_value = [(1, 1, "page text")]

    options = Options()
    options.BASE_PATH = "/dummy/input/file.pdf"
    options.OUTPUT_CSV = "/dummy/output.csv"
    options.RESUME = False

    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    mock_transform = MagicMock()
    mock_transform.transform.return_value = {"field": "value"}
    controller = Gaia(options, transform_stream=mock_transform, observer=mock_observer)

    success = controller.run(options)
    assert success is True

    # Verify that process_file was called with the direct file path
    mock_parser_instance.process_file.assert_called_once()
    call_args = mock_parser_instance.process_file.call_args[0]
    assert call_args[0] == "/dummy/input/file.pdf"
    assert call_args[1].observer == mock_observer


def test_default_output_stream_generator():
    from pyingestion.output_stream import DefaultOutputStream

    stream = DefaultOutputStream()
    stream.write({"field": "val1"})
    stream.write({"field": "val2"})

    # Test that iterating over it returns a generator yielding items
    results = list(stream)
    assert results == [{"field": "val1"}, {"field": "val2"}]


@patch("pyingestion.cli.terminal_ui.os.path.exists")
@patch("pyingestion.input_stream.InputStreamFactory")
@patch("pyingestion.cli.terminal_ui.Console")
def test_run_dump_mode_success(mock_console_class, mock_factory, mock_exists):
    mock_exists.return_value = True

    mock_parser = MagicMock()
    mock_factory.create.return_value = mock_parser
    mock_parser.process_file.return_value = [
        (1, 2, "Unit 1 Text"),
        (2, 2, "Unit 2 Text"),
    ]

    mock_console = MagicMock()
    mock_console_class.return_value = mock_console

    from pyingestion.cli.terminal_ui import run_dump_mode

    options = Options()
    options.DUMP_FILE = "/dummy/dump.pdf"
    options.PAGES_PER_UNIT = 1
    options.PARSER_TYPE = "pdf"

    with pytest.raises(SystemExit) as excinfo:
        run_dump_mode(options)

    assert excinfo.value.code == 0
    mock_parser.process_file.assert_called_once_with(
        "/dummy/dump.pdf", session=None, pages_per_unit=1
    )


@patch("pyingestion.cli.terminal_ui.os.path.exists")
@patch("pyingestion.cli.terminal_ui.Console")
def test_run_dump_mode_file_not_found(mock_console_class, mock_exists):
    mock_exists.return_value = False

    from pyingestion.cli.terminal_ui import run_dump_mode

    options = Options()
    options.DUMP_FILE = "/nonexistent/file.pdf"

    with pytest.raises(SystemExit) as excinfo:
        run_dump_mode(options)

    assert excinfo.value.code == 1
