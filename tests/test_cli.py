from unittest.mock import patch, MagicMock
import sys
import os
import json
from argparse import Namespace
import pytest

from gaia.main import main
from gaia.gaia import Gaia
from gaia.options import Options


@patch("gaia.main.argparse.ArgumentParser.parse_args")
@patch("gaia.main.run_with_ui")
def test_cli_execution_flow(mock_run_with_ui, mock_parse_args):
    # Setup mocks
    mock_args = Namespace(
        input_dir="/dummy/input",
        output="/dummy/output.csv",
        resume=False,
        regex="/dummy/regex.json",
        test=None,
        recursive=False,
        pages_per_unit=1,
        lang="en",
    )
    mock_parse_args.return_value = mock_args

    # Execute main
    main()

    # Assertions
    mock_parse_args.assert_called_once()
    mock_run_with_ui.assert_called_once()
    options_passed = mock_run_with_ui.call_args[0][0]
    assert options_passed.BASE_PATH == "/dummy/input"
    assert options_passed.OUTPUT_CSV == "/dummy/output.csv"
    assert options_passed.RESUME is False
    assert options_passed.REGEX_FILE == "/dummy/regex.json"


@patch("gaia.main.argparse.ArgumentParser.parse_args")
@patch("gaia.main.run_with_ui")
@patch("gaia.extraction_session.ExtractionSession.load_state")
def test_cli_parameterless_resume_success(
    mock_load_state, mock_run_with_ui, mock_parse_args
):
    # Setup mock arguments with input_dir = None and resume = True
    mock_args = Namespace(
        input_dir=None,
        output="/dummy/output.csv",
        resume=True,
        regex=None,
        test=None,
        recursive=False,
        pages_per_unit=1,
        lang="en",
    )
    mock_parse_args.return_value = mock_args

    # Mock CWD state file loading content
    mock_load_state.return_value = {
        "input_dir": "/loaded/input/dir",
        "output_file": "/loaded/output.csv",
        "regex_file": "/loaded/regex.json",
        "processed_files": ["f1.pdf"],
    }

    # Run main
    main()

    # Assert options contains the loaded paths from state file
    mock_run_with_ui.assert_called_once()
    options_passed = mock_run_with_ui.call_args[0][0]
    assert options_passed.BASE_PATH == "/loaded/input/dir"
    assert options_passed.OUTPUT_CSV == "/loaded/output.csv"
    assert options_passed.RESUME is True
    assert options_passed.REGEX_FILE == "/loaded/regex.json"


@patch("gaia.gaia.os.path.exists")
@patch("gaia.gaia.os.path.isdir")
@patch("gaia.gaia.NativeRegexEngine")
@patch("gaia.gaia.NativePdfParser")
@patch("gaia.gaia.DefaultOutputStream")
def test_app_controller_validations_and_run(
    mock_output_stream, mock_parser_class, mock_regex_engine, mock_isdir, mock_exists
):
    mock_exists.return_value = True
    mock_isdir.return_value = True

    mock_parser_instance = MagicMock()
    mock_parser_class.return_value = mock_parser_instance

    options = Options()
    options.BASE_PATH = "/dummy/input"
    options.OUTPUT_CSV = "/dummy/output.csv"
    options.RESUME = True
    options.REGEX_FILE = "/dummy/regex.json"

    mock_observer = MagicMock()
    controller = Gaia(options, observer=mock_observer)

    # mock os.listdir to return empty list so it finishes quickly
    with patch("gaia.gaia.os.listdir", return_value=[]):
        success = controller.run(options)

    assert success is True
    mock_exists.assert_any_call("/dummy/input")
    mock_isdir.assert_any_call("/dummy/input")


@patch("gaia.gaia.os.path.exists")
@patch("gaia.gaia.os.path.isdir")
@patch("gaia.gaia.os.remove")
@patch("gaia.gaia.NativeRegexEngine")
@patch("gaia.gaia.NativePdfParser")
def test_app_controller_log_deletion(
    mock_parser_class, mock_regex_engine, mock_remove, mock_isdir, mock_exists
):
    # Scenario 1: Resume is False -> Should remove gaia_errors.log if it exists
    mock_exists.side_effect = (
        lambda p: True
        if "gaia_errors.log" in p or p == "/dummy/input"
        else False
    )
    mock_isdir.return_value = True

    options = Options()
    options.BASE_PATH = "/dummy/input"
    options.OUTPUT_CSV = "/dummy/output.csv"
    options.RESUME = False
    options.REGEX_FILE = "/dummy/regex.json"

    mock_observer = MagicMock()
    controller = Gaia(options, observer=mock_observer)

    with patch("gaia.gaia.os.listdir", return_value=[]):
        controller.run(options)
    mock_remove.assert_called_once()

    # Scenario 2: Resume is True -> Should NOT remove gaia_errors.log
    mock_remove.reset_mock()
    options.RESUME = True
    with patch("gaia.gaia.os.listdir", return_value=[]):
        controller.run(options)
    mock_remove.assert_not_called()


@patch("gaia.gaia.os.makedirs")
@patch("gaia.gaia.os.path.exists")
@patch("gaia.gaia.os.path.isfile")
@patch("gaia.gaia.os.path.isdir")
@patch("gaia.gaia.NativeRegexEngine")
@patch("gaia.gaia.NativePdfParser")
@patch("gaia.gaia.DefaultOutputStream")
def test_gaia_run_with_direct_file(
    mock_output_stream, mock_parser_class, mock_regex_engine, mock_isdir, mock_isfile, mock_exists, mock_makedirs
):
    mock_exists.return_value = True
    mock_isdir.return_value = False
    mock_isfile.return_value = True

    mock_parser_instance = MagicMock()
    mock_parser_class.return_value = mock_parser_instance
    mock_parser_instance.process_file.return_value = [
        (1, 1, "page text")
    ]

    options = Options()
    options.BASE_PATH = "/dummy/input/file.pdf"
    options.OUTPUT_CSV = "/dummy/output.csv"
    options.RESUME = False
    options.REGEX_FILE = "/dummy/regex.json"

    mock_observer = MagicMock()
    mock_observer.is_cancelled = False
    controller = Gaia(options, observer=mock_observer)

    success = controller.run(options)
    assert success is True

    # Verify that process_file was called with the direct file path
    mock_parser_instance.process_file.assert_called_once()
    call_args = mock_parser_instance.process_file.call_args[0]
    assert call_args[0] == "/dummy/input/file.pdf"
    assert call_args[1].observer == mock_observer


def test_default_output_stream_generator():
    from gaia.output_stream import DefaultOutputStream
    stream = DefaultOutputStream()
    stream.write({"field": "val1"})
    stream.write({"field": "val2"})

    # Test that iterating over it returns a generator yielding items
    results = list(stream)
    assert results == [{"field": "val1"}, {"field": "val2"}]
