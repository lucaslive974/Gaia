import os
import json
from unittest.mock import patch, MagicMock
from argparse import Namespace
import pytest
from gaia.options import Options
from gaia.options import options as global_options
from gaia.cli.cli_helper import CliHelper
from gaia.extraction_session import ExtractionSession


@pytest.fixture
def fresh_options():
    return Options()


def test_default_values(fresh_options):
    """Test that a new Options instance has the expected default values."""
    assert fresh_options.BASE_PATH == ""
    assert fresh_options.OUTPUT_CSV == os.path.join(os.getcwd(), "output.csv")
    assert fresh_options.RESUME is False
    assert fresh_options.REGEX_FILE is None
    assert fresh_options.TEST_FILE is None
    assert fresh_options.RECURSIVE is False
    assert fresh_options.PAGES_PER_UNIT == 1
    assert fresh_options.LANG == "en"


def test_getitem_success(fresh_options):
    """Test accessing options attributes using dictionary syntax."""
    assert fresh_options["BASE_PATH"] == ""
    assert fresh_options["RESUME"] is False
    assert fresh_options["REGEX_FILE"] is None
    assert fresh_options["RECURSIVE"] is False


def test_getitem_key_error(fresh_options):
    """Test that accessing a non-existent key via dictionary syntax raises KeyError."""
    with pytest.raises(KeyError):
        _ = fresh_options["NON_EXISTENT_KEY"]


def test_setitem(fresh_options):
    """Test modifying options attributes using dictionary syntax."""
    fresh_options["BASE_PATH"] = "/custom/path"
    fresh_options["RESUME"] = True
    fresh_options["REGEX_FILE"] = "/my/regex.json"
    fresh_options["RECURSIVE"] = True

    # Verify both dictionary-like and attribute-like access reflect the changes
    assert fresh_options["BASE_PATH"] == "/custom/path"
    assert fresh_options.BASE_PATH == "/custom/path"
    assert fresh_options["RESUME"] is True
    assert fresh_options.RESUME is True
    assert fresh_options["REGEX_FILE"] == "/my/regex.json"
    assert fresh_options["RECURSIVE"] is True
    assert fresh_options.RECURSIVE is True


def test_contains(fresh_options):
    """Test the 'in' operator on the options object."""
    assert "BASE_PATH" in fresh_options
    assert "OUTPUT_CSV" in fresh_options
    assert "RESUME" in fresh_options
    assert "REGEX_FILE" in fresh_options
    assert "RECURSIVE" in fresh_options
    assert "NON_EXISTENT_KEY" not in fresh_options


def test_setattr_validation_ppu(fresh_options):
    with pytest.raises(ValueError):
        fresh_options.PAGES_PER_UNIT = 0
    with pytest.raises(ValueError):
        fresh_options.PAGES_PER_UNIT = -1
    with pytest.raises(ValueError):
        fresh_options.PAGES_PER_UNIT = "invalid"


def test_setattr_validation_lang(fresh_options):
    with pytest.raises(ValueError):
        fresh_options.LANG = "fr"
    fresh_options.LANG = "pt"
    assert fresh_options.LANG == "pt"


def test_list_attr(fresh_options):
    attrs = fresh_options.list_attr()
    assert ("input_dir", "BASE_PATH") in attrs
    assert ("output", "OUTPUT_CSV") in attrs
    assert ("resume", "RESUME") in attrs
    assert ("lang", "LANG") in attrs


def test_parse_and_build_options_all_fields():
    """Test parse_and_build_options with a Namespace containing all mapped attributes."""
    args = Namespace(
        input_dir="/my/input",
        output="/my/output.csv",
        resume=True,
        regex="/my/regex.json",
        test=None,
        recursive=True,
        pages_per_unit=5,
        lang="pt",
    )
    options = CliHelper.parse_and_build_options(args)

    assert options.BASE_PATH == "/my/input"
    assert options.OUTPUT_CSV == "/my/output.csv"
    assert options.RESUME is True
    assert options.REGEX_FILE == "/my/regex.json"
    assert options.RECURSIVE is True
    assert options.PAGES_PER_UNIT == 5
    assert options.LANG == "pt"


def test_parse_and_build_options_partial_fields():
    """Test parse_and_build_options with a Namespace containing only some mapped attributes."""
    args = Namespace(
        input_dir="/my/input_only",
        regex="/my/regex.json",
        # other attributes are missing
    )
    options = CliHelper.parse_and_build_options(args)

    # Check that present fields were updated
    assert options.BASE_PATH == "/my/input_only"
    assert options.REGEX_FILE == "/my/regex.json"
    # Check that missing fields retained their defaults
    assert options.RESUME is False
    assert options.RECURSIVE is False
    assert options.OUTPUT_CSV == os.path.join(os.getcwd(), "output.csv")


def test_parse_and_build_options_unmapped_fields_ignored():
    """Test that parse_and_build_options ignores attributes not in the mapping."""
    args = Namespace(
        input_dir="/my/input",
        regex="/my/regex.json",
        extra_arg="some_value",
    )
    options = CliHelper.parse_and_build_options(args)

    assert options.BASE_PATH == "/my/input"
    assert options.REGEX_FILE == "/my/regex.json"
    # Ensure extra arg is not set on options
    assert hasattr(options, "extra_arg") is False
    assert ("extra_arg" in options) is False


def test_parse_and_build_options_value_errors():
    # Scenario 1: missing input_dir, resume = False -> should raise ValueError
    args = Namespace(
        input_dir=None, resume=False, output="/my/output.csv", regex="/my/regex.json"
    )
    with pytest.raises(ValueError):
        CliHelper.parse_and_build_options(args)

    # Scenario 2: missing input_dir, resume = True but no state file -> should raise ValueError
    with patch("gaia.extraction_session.ExtractionSession.load_state", return_value=None):
        args = Namespace(
            input_dir=None, resume=True, output="/my/output.csv", regex="/my/regex.json"
        )
        with pytest.raises(ValueError):
            CliHelper.parse_and_build_options(args)

    # Scenario 3: input_dir provided, resume = False, but regex is missing -> should raise ValueError
    args = Namespace(
        input_dir="/my/input", resume=False, output="/my/output.csv", regex=None
    )
    with pytest.raises(ValueError):
        CliHelper.parse_and_build_options(args)

    # Scenario 4: test mode provided -> input_dir is not required, but regex is required
    args = Namespace(
        input_dir=None,
        resume=False,
        output="/my/output.csv",
        regex="/my/regex.json",
        test="/my/test.pdf",
    )
    options = CliHelper.parse_and_build_options(args)
    assert options.TEST_FILE == "/my/test.pdf"
    assert options.REGEX_FILE == "/my/regex.json"

    # Scenario 5: pages_per_unit less than 1 -> should raise ValueError
    args = Namespace(
        input_dir="/my/input",
        resume=False,
        output="/my/output.csv",
        regex="/my/regex.json",
        pages_per_unit=0,
    )
    with pytest.raises(ValueError):
        CliHelper.parse_and_build_options(args)

    # Scenario 6: pages_per_unit is negative -> should raise ValueError
    args = Namespace(
        input_dir="/my/input",
        resume=False,
        output="/my/output.csv",
        regex="/my/regex.json",
        pages_per_unit=-5,
    )
    with pytest.raises(ValueError):
        CliHelper.parse_and_build_options(args)

    # Scenario 7: pages_per_unit is not an integer -> should raise ValueError
    args = Namespace(
        input_dir="/my/input",
        resume=False,
        output="/my/output.csv",
        regex="/my/regex.json",
        pages_per_unit="abc",
    )
    with pytest.raises(ValueError):
        CliHelper.parse_and_build_options(args)


def test_global_options_instance():
    """Test that the global options instance exported by the package functions properly."""
    assert "BASE_PATH" in global_options
    assert "OUTPUT_CSV" in global_options
    assert "RESUME" in global_options


def test_load_save_clear_resume_state():
    input_dir = "/dummy/input"
    state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
    state_file_input = os.path.join(input_dir, ".gaia_resume.json")

    options = Options()
    options.BASE_PATH = input_dir
    options.REGEX_FILE = "/my/regex.json"

    session = ExtractionSession(None)
    session.input_dir = options.BASE_PATH
    session.output_file = options.OUTPUT_CSV
    session.regex_file = options.REGEX_FILE
    session.processed_files = ["file1.pdf"]
    session.successful_pages = 10
    session.failed_pages = 2
    session.total_pages = 12

    with patch("gaia.extraction_session.open", create=True) as mock_open:
        session.save_state()
        mock_open.assert_any_call(state_file_cwd, "w", encoding="utf-8")
        mock_open.assert_any_call(state_file_input, "w", encoding="utf-8")

    with patch("gaia.extraction_session.os.path.exists") as mock_exists, patch(
        "gaia.extraction_session.open", create=True
    ) as mock_open:
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(
            {
                "input_dir": input_dir,
                "output_file": options.OUTPUT_CSV,
                "regex_file": "/my/regex.json",
                "processed_files": ["file1.pdf"],
                "successful_pages": 10,
                "failed_pages": 2,
                "total_pages": 12,
            }
        )
        mock_open.return_value.__enter__.return_value = mock_file

        state = ExtractionSession.load_state(input_dir)
        assert state is not None
        assert state["processed_files"] == ["file1.pdf"]
        assert state["regex_file"] == "/my/regex.json"

    with patch("gaia.extraction_session.os.path.exists") as mock_exists, patch(
        "gaia.extraction_session.os.remove"
    ) as mock_remove:
        mock_exists.return_value = True
        session.clear_state()
        mock_remove.assert_any_call(state_file_cwd)
        mock_remove.assert_any_call(state_file_input)
