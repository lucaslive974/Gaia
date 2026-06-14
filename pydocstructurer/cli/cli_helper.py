import os
import json
from typing import Any
from argparse import Namespace
from pydocstructurer.options import Options
from pydocstructurer.extraction_session import ExtractionSession
from pydocstructurer.i18n import _, set_lang


class CliHelper:
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
            "regex": "REGEX_FILE",
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
            options.LANG = lang

        # 3. Bind remaining CLI arguments that are explicitly provided (not None)
        for attr in Options.list_attr():
            if attr[0] == "lang":
                continue

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
                    if state.get("regex_file"):
                        options.REGEX_FILE = state.get("regex_file")
                else:
                    raise ValueError(_("err_resume_no_state"))
            else:
                raise ValueError(_("err_input_dir_required"))

        # 5. Check for required regex file if not resuming and not in dump mode
        if not is_dump:
            if not options.RESUME:
                if not options.REGEX_FILE:
                    raise ValueError(_("err_regex_required_normal"))
            else:
                # If resuming, load state to autoload regex
                state = ExtractionSession.load_state(options.BASE_PATH)
                if state:
                    if state.get("output_file"):
                        options.OUTPUT_CSV = state.get("output_file")
                    if state.get("regex_file"):
                        options.REGEX_FILE = state.get("regex_file")

                # Still, we must have a regex file to resume
                if not options.REGEX_FILE:
                    raise ValueError(_("err_regex_required_resume"))


        return options

