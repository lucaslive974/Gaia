import os
import json
from unittest.mock import patch, MagicMock
from argparse import Namespace
import pytest
from pyingestion.options import Options
from pyingestion.options import options as global_options
from pyingestion.cli.cli_helper import CliHelper
from pyingestion.extraction_session import ExtractionSession
from pyingestion.i18n import Language, get_lang


class TestOptionsDefaultsAndAccess:
    def test_default_values(self, fresh_options):
        assert fresh_options.BASE_PATH == ""
        assert fresh_options.OUTPUT_CSV == os.path.join(os.getcwd(), "output.csv")
        assert fresh_options.RESUME is False
        assert fresh_options.TEST_FILE is None
        assert fresh_options.DUMP_FILE is None
        assert fresh_options.RECURSIVE is False
        assert fresh_options.PAGES_PER_UNIT == 1
        assert fresh_options.PARSER_TYPE == "pdf"

    def test_dictionary_syntax_access(self, fresh_options):
        assert fresh_options["BASE_PATH"] == ""
        assert fresh_options["RESUME"] is False
        assert fresh_options["RECURSIVE"] is False

    def test_dictionary_syntax_key_error(self, fresh_options):
        with pytest.raises(KeyError):
            _ = fresh_options["NON_EXISTENT_KEY"]

    def test_dictionary_syntax_modification(self, fresh_options):
        fresh_options["BASE_PATH"] = "/custom/path"
        fresh_options["RESUME"] = True
        fresh_options["RECURSIVE"] = True

        assert fresh_options["BASE_PATH"] == "/custom/path"
        assert fresh_options.BASE_PATH == "/custom/path"
        assert fresh_options["RESUME"] is True
        assert fresh_options["RECURSIVE"] is True


    def test_contains_operator(self, fresh_options):
        assert "BASE_PATH" in fresh_options
        assert "OUTPUT_CSV" in fresh_options
        assert "RESUME" in fresh_options
        assert "NON_EXISTENT_KEY" not in fresh_options

    def test_list_attr(self, fresh_options):
        attrs = fresh_options.list_attr()
        assert ("input_dir", "BASE_PATH") in attrs
        assert ("output", "OUTPUT_CSV") in attrs
        assert ("resume", "RESUME") in attrs
        assert ("type", "PARSER_TYPE") in attrs
        assert ("dump", "DUMP_FILE") in attrs

    def test_global_options_instance(self):
        assert "BASE_PATH" in global_options
        assert "OUTPUT_CSV" in global_options
        assert "RESUME" in global_options


class TestOptionsSetAttrValidations:
    @pytest.mark.parametrize("invalid_ppu", [0, -1, -100, "invalid", "abc", None])
    def test_pages_per_unit_validation(self, fresh_options, invalid_ppu):
        with pytest.raises(ValueError):
            fresh_options.PAGES_PER_UNIT = invalid_ppu

    @pytest.mark.parametrize("valid_type", ["pdf", "docx", "ocr"])
    def test_parser_type_validation_success(self, fresh_options, valid_type):
        fresh_options.PARSER_TYPE = valid_type
        assert fresh_options.PARSER_TYPE == valid_type

    def test_parser_type_validation_failure(self, fresh_options):
        with pytest.raises(ValueError):
            fresh_options.PARSER_TYPE = "invalid"


class TestCliHelperParsing:
    def test_parse_all_fields(self):
        args = Namespace(
            input_dir="/my/input",
            output="/my/output.csv",
            resume=True,
            test=None,
            recursive=True,
            pages_per_unit=5,
            lang="pt",
        )
        options = CliHelper.parse_and_build_options(args)
        assert options.BASE_PATH == "/my/input"
        assert options.OUTPUT_CSV == "/my/output.csv"
        assert options.RESUME is True
        assert options.RECURSIVE is True
        assert options.PAGES_PER_UNIT == 5
        assert get_lang() == Language.PT_BR

    def test_parse_partial_fields(self):
        args = Namespace(
            input_dir="/my/input_only",
        )
        options = CliHelper.parse_and_build_options(args)
        assert options.BASE_PATH == "/my/input_only"
        assert options.RESUME is False
        assert options.RECURSIVE is False

    def test_ignore_unmapped_fields(self):
        args = Namespace(
            input_dir="/my/input",
            extra_arg="some_value",
        )
        options = CliHelper.parse_and_build_options(args)
        assert options.BASE_PATH == "/my/input"
        assert hasattr(options, "extra_arg") is False

    def test_dump_mode_bypasses_validations(self):
        args = Namespace(
            input_dir=None,
            resume=False,
            output="/my/output.csv",
            regex=None,
            test=None,
            dump="/my/dump.pdf",
            pages_per_unit=1,
            lang="en",
        )
        options = CliHelper.parse_and_build_options(args)
        assert options.DUMP_FILE == "/my/dump.pdf"
        assert options.BASE_PATH == ""

    def test_test_mode_bypasses_input_dir(self):
        args = Namespace(
            input_dir=None,
            resume=False,
            output="/my/output.csv",
            test="/my/test.pdf",
        )
        options = CliHelper.parse_and_build_options(args)
        assert options.TEST_FILE == "/my/test.pdf"
        assert options.BASE_PATH == ""

    def test_parameterless_resume_success(self):
        with patch(
            "pyingestion.extraction_session.ExtractionSession.load_state"
        ) as mock_load_state:
            mock_load_state.return_value = {
                "input_dir": "/loaded/input/dir",
                "output_file": "/loaded/output.csv",
                "regex_file": "/loaded/regex.json",
                "processed_files": ["f1.pdf"],
            }
            args = Namespace(
                input_dir=None,
                output="/dummy/output.csv",
                resume=True,
                test=None,
                recursive=False,
                pages_per_unit=1,
                lang="en",
            )
            options = CliHelper.parse_and_build_options(args)
            assert options.BASE_PATH == "/loaded/input/dir"
            assert options.OUTPUT_CSV == "/loaded/output.csv"
            assert options.RESUME is True


class TestCliHelperValidationErrors:
    def test_missing_input_dir(self):
        args = Namespace(input_dir=None, resume=False)
        with pytest.raises(ValueError, match="positional argument"):
            CliHelper.parse_and_build_options(args)

    def test_missing_input_dir_and_no_resume_state(self):
        with patch(
            "pyingestion.extraction_session.ExtractionSession.load_state",
            return_value=None,
        ):
            args = Namespace(input_dir=None, resume=True)
            with pytest.raises(ValueError, match="resume state"):
                CliHelper.parse_and_build_options(args)

    def test_missing_regex_file(self):
        args = Namespace(input_dir="/my/input", resume=False, regex=None)
        options = CliHelper.parse_and_build_options(args)
        with pytest.raises(ValueError, match="(?i)regex"):
            CliHelper.build_transform(args, options)

    @pytest.mark.parametrize("invalid_ppu", [0, -5, "abc"])
    def test_invalid_pages_per_unit(self, invalid_ppu):
        args = Namespace(
            input_dir="/my/input",
            resume=False,
            pages_per_unit=invalid_ppu,
        )
        with pytest.raises(ValueError):
            CliHelper.parse_and_build_options(args)



class TestCliHelperConfig:
    def test_detect_config_format(self):
        assert CliHelper._detect_config_format("settings.toml") == "toml"
        assert CliHelper._detect_config_format("settings.TOML") == "toml"
        assert CliHelper._detect_config_format("settings.json") == "json"
        assert CliHelper._detect_config_format("settings.txt") == "json"

    def test_load_valid_toml_config_file(self, temp_file_factory):
        toml_content = """
        [config]
        input_dir = "/toml/input"
        output = "/toml/output.csv"
        resume = true
        recursive = true
        regex = "/toml/regex.toml"
        pages_per_unit = 3
        type = "docx"
        """
        config_file = temp_file_factory("config.toml", toml_content)
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
        assert options.BASE_PATH == "/toml/input"
        assert options.OUTPUT_CSV == "/toml/output.csv"
        assert options.RESUME is True
        assert options.RECURSIVE is True
        assert options.PAGES_PER_UNIT == 3
        assert options.PARSER_TYPE == "docx"

        # Check that build_transform parses regex path from config file
        with patch("pyingestion.regex_engine.NativeRegexEngine.from_file") as mock_from_file:
            CliHelper.build_transform(args, options)
            mock_from_file.assert_called_once_with("/toml/regex.toml")

    def test_load_valid_json_config_file(self, temp_file_factory):
        json_data = {
            "config": {
                "input_dir": "/json/input",
                "output": "/json/output.csv",
                "resume": False,
                "recursive": False,
                "regex": "/json/regex.json",
                "pages_per_unit": 2,
                "type": "pdf",
            }
        }
        config_file = temp_file_factory("config.json", json_data, is_json=True)
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
        assert options.BASE_PATH == "/json/input"
        assert options.OUTPUT_CSV == "/json/output.csv"
        assert options.RESUME is False
        assert options.RECURSIVE is False
        assert options.PAGES_PER_UNIT == 2
        assert options.PARSER_TYPE == "pdf"

        # Check that build_transform parses regex path from config file
        with patch("pyingestion.regex_engine.NativeRegexEngine.from_file") as mock_from_file:
            CliHelper.build_transform(args, options)
            mock_from_file.assert_called_once_with("/json/regex.json")


    def test_config_precedence(self, temp_file_factory):
        toml_content = """
        [config]
        input_dir = "/toml/input"
        output = "/toml/output.csv"
        resume = true
        recursive = true
        pages_per_unit = 3
        type = "docx"
        """
        config_file = temp_file_factory("config.toml", toml_content)
        args = Namespace(
            config=config_file,
            input_dir="/cli/override/input",
            output="/cli/override/output.csv",
            resume=None,
            recursive=False,
            regex="/dummy/regex.json",
            test=None,
            dump=None,
            pages_per_unit=None,
            lang="pt",
            type=None,
        )
        options = CliHelper.parse_and_build_options(args)
        assert options.BASE_PATH == "/cli/override/input"
        assert options.OUTPUT_CSV == "/cli/override/output.csv"
        assert options.RECURSIVE is False
        assert options.RESUME is True
        assert options.PAGES_PER_UNIT == 3
        assert get_lang() == Language.PT_BR
        assert options.PARSER_TYPE == "docx"

    def test_config_file_not_found(self):
        args = Namespace(config="/nonexistent/path.toml")
        with pytest.raises(FileNotFoundError):
            CliHelper.parse_and_build_options(args)

    def test_malformed_toml_file(self, temp_file_factory):
        bad_toml = temp_file_factory("bad.toml", "invalid = [toml")
        args = Namespace(config=bad_toml)
        with pytest.raises(ValueError, match="(?i)toml"):
            CliHelper.parse_and_build_options(args)

    def test_malformed_json_file(self, temp_file_factory):
        bad_json = temp_file_factory("bad.json", "invalid json")
        args = Namespace(config=bad_json)
        with pytest.raises(ValueError, match="(?i)json"):
            CliHelper.parse_and_build_options(args)

    def test_missing_config_section(self, temp_file_factory):
        missing_sec = temp_file_factory("missing_sec.toml", "input_dir = '/toml/input'")
        args = Namespace(config=missing_sec)
        with pytest.raises(ValueError, match="(?i)config"):
            CliHelper.parse_and_build_options(args)



class TestResumeStateIntegration:
    def test_load_save_clear_resume_state(self):
        input_dir = "/dummy/input"
        state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
        state_file_input = os.path.join(input_dir, ".gaia_resume.json")

        options = Options()
        options.BASE_PATH = input_dir

        session = ExtractionSession(None)
        session.input_dir = options.BASE_PATH
        session.output_file = options.OUTPUT_CSV
        session.config_file = "/my/regex.json"
        session.processed_files = ["file1.pdf"]
        session.successful_pages = 10
        session.failed_pages = 2
        session.total_pages = 12


        with patch("pyingestion.extraction_session.open", create=True) as mock_open:
            session.save_state()
            mock_open.assert_any_call(state_file_cwd, "w", encoding="utf-8")
            mock_open.assert_any_call(state_file_input, "w", encoding="utf-8")

        with (
            patch("pyingestion.extraction_session.os.path.exists") as mock_exists,
            patch("pyingestion.extraction_session.open", create=True) as mock_open,
        ):
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
            assert state["config_file"] == "/my/regex.json"

        with (
            patch("pyingestion.extraction_session.os.path.exists") as mock_exists,
            patch("pyingestion.extraction_session.os.remove") as mock_remove,
        ):
            mock_exists.return_value = True
            session.clear_state()
            mock_remove.assert_any_call(state_file_cwd)
            mock_remove.assert_any_call(state_file_input)


class TestParserFactory:
    def test_parser_factory_resolution(self):
        from pyingestion.parser import ParserFactory, ParserType
        from pyingestion.parsers import PdfParser

        parser_str = ParserFactory.create("pdf")
        assert isinstance(parser_str, PdfParser)

        parser_enum = ParserFactory.create(ParserType.PDF)
        assert isinstance(parser_enum, PdfParser)

        with pytest.raises(ValueError):
            ParserFactory.create("invalid")
