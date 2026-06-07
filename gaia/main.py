import sys
import argparse
from gaia.config.options import Options
from gaia.cli.cli_helper import CliHelper
from gaia.cli.terminal_ui import run_with_ui
from gaia.i18n import _, set_lang


def main():
    # Pre-parse lang flag from sys.argv
    lang = "en"
    for idx, arg in enumerate(sys.argv):
        if arg in ("--lang", "-l"):
            if idx + 1 < len(sys.argv):
                lang = sys.argv[idx + 1]
            break
    if lang in ("en", "pt"):
        set_lang(lang)

    parser = argparse.ArgumentParser(
        description=_("cli_desc")
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
        default=Options.OUTPUT_CSV,
        help=_("cli_output_help", default_csv=Options.OUTPUT_CSV),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=_("cli_resume_help"),
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
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
        "-p",
        "--pages-per-unit",
        type=int,
        default=1,
        help=_("cli_pages_per_unit_help"),
    )
    parser.add_argument(
        "-l",
        "--lang",
        type=str,
        choices=["en", "pt"],
        default="en",
        help=_("cli_lang_help"),
    )

    args = parser.parse_args()

    try:
        options = CliHelper.parse_and_build_options(args)
    except ValueError as e:
        parser.error(str(e))

    if options.TEST_FILE:
        from gaia.cli.terminal_ui import run_test_mode
        run_test_mode(options)
    else:
        run_with_ui(options)


if __name__ == "__main__":
    main()


