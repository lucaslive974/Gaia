import os
import json
import argparse
from typing import Any
from argparse import Namespace
from pyingestion.options import Options
from pyingestion.extraction_session import ExtractionSession
from pyingestion.i18n import _, set_lang


class CliHelper:
    @classmethod
    def get_argument_parser(cls) -> argparse.ArgumentParser:
        import tomllib

        parser = argparse.ArgumentParser(description=_("cli_desc"))

        config_file_path = os.path.join(os.path.dirname(__file__), "cli_arguments.toml")
        with open(config_file_path, "rb") as f:
            args_config = tomllib.load(f)

        for arg_def in args_config.get("arguments", []):
            args_list = arg_def["flags"]
            kwargs = {}

            if "action" in arg_def:
                kwargs["action"] = arg_def["action"]
            if "type" in arg_def:
                type_str = arg_def["type"]
                if type_str == "int":
                    kwargs["type"] = int
                else:
                    kwargs["type"] = str
            if "nargs" in arg_def:
                kwargs["nargs"] = arg_def["nargs"]
            if "choices" in arg_def:
                kwargs["choices"] = arg_def["choices"]
            if "metavar" in arg_def:
                kwargs["metavar"] = arg_def["metavar"]

            kwargs["default"] = None

            help_key = arg_def["help"]
            if help_key == "cli_output_help":
                kwargs["help"] = _(help_key, default_csv=Options.OUTPUT_CSV)
            else:
                kwargs["help"] = _(help_key)

            parser.add_argument(*args_list, **kwargs)

        return parser

    @classmethod
    def _detect_config_format(cls, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".toml":
            return "toml"
        return "json"

    @classmethod
    def _load_toml(cls, file_path: str) -> dict[str, Any]:
        import tomllib

        try:
            with open(file_path, "rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(_("err_config_toml_parse", error=e))
        except Exception as e:
            raise ValueError(_("err_config_read", error=e))

    @classmethod
    def _load_json(cls, file_path: str) -> dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(_("err_config_json_parse", error=e))
        except Exception as e:
            raise ValueError(_("err_config_read", error=e))

    @classmethod
    def _load_config_file(cls, file_path: str) -> dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(_("err_config_not_found", file_path=file_path))
        fmt = cls._detect_config_format(file_path)
        if fmt == "toml":
            return cls._load_toml(file_path)
        return cls._load_json(file_path)

    @classmethod
    def parse_and_build_options(cls, args: Namespace) -> Options:
        options = Options()

        config_mapping = {
            "input_dir": "BASE_PATH",
            "output": "OUTPUT_CSV",
            "resume": "RESUME",
            "recursive": "RECURSIVE",
            "test": "TEST_FILE",
            "dump": "DUMP_FILE",
            "pages_per_unit": "PAGES_PER_UNIT",
            "type": "PARSER_TYPE",
        }

        # 1. Load config file if provided
        config_data: dict[str, Any] = {}
        config_path = getattr(args, "config", None)
        if config_path:
            raw_data = cls._load_config_file(config_path)
            if "config" in raw_data and isinstance(raw_data["config"], dict):
                config_data = raw_data["config"]
            else:
                raise ValueError(_("err_config_missing_section"))

            for k, v in config_data.items():
                opt_attr = config_mapping.get(k)
                if opt_attr and v is not None:
                    setattr(options, opt_attr, v)

        # 2. Set and validate language first so errors are translated
        lang = getattr(args, "lang", None)
        if isinstance(lang, str):
            if lang not in ("en", "pt"):
                raise ValueError(_("err_lang_invalid"))
            set_lang(lang)

        # 3. Bind remaining CLI arguments that are explicitly provided (not None)
        for attr in Options.list_attr():
            if hasattr(args, attr[0]):
                val = getattr(args, attr[0])
                if val is not None:
                    setattr(options, attr[1], val)

        is_test = options.TEST_FILE is not None
        is_dump = options.DUMP_FILE is not None

        # 4. Verify and autoload input_dir if resume is requested and it is missing
        if not options.BASE_PATH and not is_test and not is_dump:
            if options.RESUME:
                state = ExtractionSession.load_state()
                if state and state.get("input_dir"):
                    options.BASE_PATH = state.get("input_dir")
                    if state.get("output_file"):
                        options.OUTPUT_CSV = state.get("output_file")
                else:
                    raise ValueError(_("err_resume_no_state"))
            else:
                raise ValueError(_("err_input_dir_required"))

        return options

    @classmethod
    def build_transform(cls, args: Namespace, options: Options) -> Any:
        from pyingestion.transform_stream import NativeRegexEngine

        is_dump = options.DUMP_FILE is not None
        if is_dump:
            return None

        # 1. Read regex path from CLI arguments, configuration file, or environment
        regex_path = getattr(args, "regex", None)

        # Or look in config file if provided
        config_path = getattr(args, "config", None)
        if not regex_path and config_path:
            raw_data = cls._load_config_file(config_path)
            if "config" in raw_data and isinstance(raw_data["config"], dict):
                regex_path = raw_data["config"].get("regex")

        # 2. Autoload from resume state if needed
        if not regex_path and options.RESUME:
            state = ExtractionSession.load_state(options.BASE_PATH)
            if state:
                # Support both new "config_file" and legacy "regex_file" key in state json
                regex_path = state.get("config_file") or state.get("regex_file")

        if not regex_path:
            if options.RESUME:
                raise ValueError(_("err_regex_required_resume"))
            else:
                raise ValueError(_("err_regex_required_normal"))

        return NativeRegexEngine.from_file(regex_path)

