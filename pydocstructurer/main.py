import sys
import os
import argparse
from pydocstructurer.options import Options
from pydocstructurer.cli.cli_helper import CliHelper
from pydocstructurer.cli.terminal_ui import run_with_ui
from pydocstructurer.i18n import _, set_lang, parse_lang_from_argv



def main():
    lang = parse_lang_from_argv(sys.argv)
    set_lang(lang)


    parser = CliHelper.get_argument_parser()
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
