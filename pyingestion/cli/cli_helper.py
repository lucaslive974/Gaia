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
            "to": "TO",
        }

        # 1. Load config file if provided
        config_data: dict[str, Any] = {}
        config_path = getattr(args, "config", None)
        if config_path:
            raw_data = cls._load_config_file(config_path)
            if "config" in raw_data and isinstance(raw_data["config"], dict):
                config_data = raw_data["config"]
            else:
                config_data = raw_data

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
    def build_pipeline(cls, args: Namespace, options: Options) -> tuple[Any, Any, Any]:
        config_path = getattr(args, "config", None)
        raw_config = {}
        if config_path:
            raw_config = cls._load_config_file(config_path)

        input_stream = cls._build_input_stream(args, options, raw_config)
        transform_stream = cls._build_transform_stream(args, options, raw_config)
        output_stream = cls._build_output_stream(args, options, raw_config)

        return input_stream, transform_stream, output_stream

    @classmethod
    def _build_input_stream(cls, args: Namespace, options: Options, raw_config: dict) -> Any:
        from pyingestion.input_stream import InputStreamFactory

        input_section = raw_config.get("input")
        if isinstance(input_section, dict):
            input_type = input_section.get("type", options.PARSER_TYPE)
            pages_per_unit = input_section.get("pages_per_unit")
            if pages_per_unit is not None:
                options.PAGES_PER_UNIT = int(pages_per_unit)
            return InputStreamFactory.create(input_type)

        return InputStreamFactory.create(options.PARSER_TYPE)

    @classmethod
    def build_transform(cls, args: Namespace, options: Options) -> Any:
        config_path = getattr(args, "config", None)
        raw_config = {}
        if config_path:
            raw_config = cls._load_config_file(config_path)
        return cls._build_transform_stream(args, options, raw_config)

    @classmethod
    def _build_transform_stream(cls, args: Namespace, options: Options, raw_config: dict) -> Any:
        from pyingestion.transform_stream import NativeRegexEngine, ChainedTransformStream

        transform_data = raw_config.get("transform")
        if not transform_data:
            # Fallback to CLI arguments or resume state
            regex_path = getattr(args, "regex", None)
            if not regex_path:
                config_sect = raw_config.get("config")
                if isinstance(config_sect, dict):
                    regex_path = config_sect.get("regex")
                elif isinstance(raw_config, dict):
                    regex_path = raw_config.get("regex")

            if not regex_path and options.RESUME:
                state = ExtractionSession.load_state(options.BASE_PATH)
                if state:
                    regex_path = state.get("config_file") or state.get("regex_file")

            if not regex_path:
                is_dump = options.DUMP_FILE is not None
                if is_dump:
                    return None
                if options.RESUME:
                    raise ValueError(_("err_regex_required_resume"))
                else:
                    raise ValueError(_("err_regex_required_normal"))
            return NativeRegexEngine.from_file(regex_path)

        def instantiate_transform(item: dict) -> Any:
            t_type = item.get("type")
            if t_type == "regex":
                rules_file = item.get("config_file") or item.get("rules_file")
                if not rules_file:
                    raise ValueError("Transform of type 'regex' requires 'config_file' or 'rules_file'.")
                return NativeRegexEngine.from_file(rules_file)
            else:
                raise ValueError(f"Unknown transform type: {t_type}")

        if isinstance(transform_data, list):
            transforms = [instantiate_transform(item) for item in transform_data]
            if len(transforms) == 1:
                return transforms[0]
            return ChainedTransformStream(transforms)
        elif isinstance(transform_data, dict):
            return instantiate_transform(transform_data)

        raise ValueError("The 'transform' section must be a dictionary or a list of dictionaries.")

    @classmethod
    def _build_output_stream(cls, args: Namespace, options: Options, raw_config: dict) -> Any:
        from pyingestion.output_stream import (
            CsvWriteStream,
            SqliteOutputStream,
            MysqlOutputStream,
            MultiOutputStream,
        )

        output_data = raw_config.get("output")
        if not output_data:
            to_dest = options.TO
            is_dump = options.DUMP_FILE is not None
            if is_dump:
                return None

            if to_dest == "sqlite":
                db_path = options.OUTPUT_CSV
                if db_path.endswith(".csv"):
                    db_path = db_path[:-4] + ".db"
                return SqliteOutputStream(db_path)
            elif to_dest == "mysql":
                connection_uri = os.environ.get("DATABASE_URL")
                if not connection_uri:
                    raise ValueError("Environment variable 'DATABASE_URL' is required for MySQL output (format: mysql://user:password@host:port/database).")
                return MysqlOutputStream(connection_uri=connection_uri)
            else:
                return CsvWriteStream(options.OUTPUT_CSV)

        def instantiate_output(item: dict) -> Any:
            out_type = item.get("type")
            if out_type == "csv":
                out_path = item.get("path") or item.get("output") or options.OUTPUT_CSV
                return CsvWriteStream(out_path)
            elif out_type == "sqlite":
                db_path = item.get("db_path") or item.get("path") or "records.db"
                table_name = item.get("table_name") or item.get("table") or "extracted_data"
                return SqliteOutputStream(db_path, table_name)
            elif out_type == "mysql":
                conn_uri = item.get("connection_uri") or item.get("connection") or os.environ.get("DATABASE_URL")
                if not conn_uri:
                    raise ValueError("MySQL output requires 'connection_uri' or env var 'DATABASE_URL'.")
                table_name = item.get("table_name") or item.get("table") or "extracted_data"
                return MysqlOutputStream(connection_uri=conn_uri, table_name=table_name)
            else:
                raise ValueError(f"Unknown output type: {out_type}")

        if isinstance(output_data, list):
            outputs = [instantiate_output(item) for item in output_data]
            if len(outputs) == 1:
                return outputs[0]
            return MultiOutputStream(outputs)
        elif isinstance(output_data, dict):
            return instantiate_output(output_data)

        raise ValueError("The 'output' section must be a dictionary or a list of dictionaries.")

