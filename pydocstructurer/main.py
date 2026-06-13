import sys
import os
import json
import argparse
from pydocstructurer.options import Options
from pydocstructurer.cli.cli_helper import CliHelper
from pydocstructurer.cli.terminal_ui import run_with_ui
from pydocstructurer.i18n import _, set_lang


def main():
    # Pre-parse lang or config flag from sys.argv
    lang = "en"
    config_path = None
    for idx, arg in enumerate(sys.argv):
        if arg in ("--config", "-c"):
            if idx + 1 < len(sys.argv):
                config_path = sys.argv[idx + 1]
        elif arg in ("--lang", "-l"):
            if idx + 1 < len(sys.argv):
                lang = sys.argv[idx + 1]

    if config_path and os.path.exists(config_path):
        try:
            ext = os.path.splitext(config_path)[1].lower()
            if ext == ".toml":
                import tomllib
                with open(config_path, "rb") as f:
                    config_data = tomllib.load(f)
            else:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

            if "--lang" not in sys.argv and "-l" not in sys.argv:
                if "lang" in config_data:
                    lang = config_data["lang"]
        except Exception:
            pass

    if lang in ("en", "pt"):
        set_lang(lang)

    parser = argparse.ArgumentParser(
        description=_("cli_desc")
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help=_("cli_config_help"),
    )
    parser.add_argument(
        "input_dir",
        type=str,
        nargs="?",
        default=None,
        help=_("cli_input_dir_help"),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help=_("cli_output_help", default_csv=Options.OUTPUT_CSV),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=None,
        help=_("cli_resume_help"),
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=None,
        help=_("cli_recursive_help"),
    )
    parser.add_argument(
        "-g",
        "--regex",
        type=str,
        default=None,
        help=_("cli_regex_help"),
    )
    parser.add_argument(
        "-t",
        "--test",
        type=str,
        default=None,
        metavar="FILE_PATH",
        help=_("cli_test_help"),
    )
    parser.add_argument(
        "-d",
        "--dump",
        type=str,
        default=None,
        metavar="FILE_PATH",
        help=_("cli_dump_help"),
    )
    parser.add_argument(
        "-p",
        "--pages-per-unit",
        type=int,
        default=None,
        help=_("cli_pages_per_unit_help"),
    )
    parser.add_argument(
        "-l",
        "--lang",
        type=str,
        choices=["en", "pt"],
        default=None,
        help=_("cli_lang_help"),
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["pdf", "docx", "ocr"],
        default=None,
        help=_("cli_type_help"),
    )


    args = parser.parse_args()

    try:
        options = CliHelper.parse_and_build_options(args)
    except ValueError as e:
        parser.error(str(e))

    if options.DUMP_FILE:
        from pydocstructurer.cli.terminal_ui import run_dump_mode
        run_dump_mode(options)
    elif options.TEST_FILE:
        from pydocstructurer.cli.terminal_ui import run_test_mode
        run_test_mode(options)
    else:
        run_with_ui(options)


if __name__ == "__main__":
    main()


