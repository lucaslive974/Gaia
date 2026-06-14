import sys
from pyingestion.cli.cli_helper import CliHelper
from pyingestion.cli.terminal_ui import run_with_ui
from pyingestion.i18n import set_lang, parse_lang_from_argv


def main():
    lang = parse_lang_from_argv(sys.argv)
    set_lang(lang)

    parser = CliHelper.get_argument_parser()
    args = parser.parse_args()

    try:
        options = CliHelper.parse_and_build_options(args)
        transform_stream = CliHelper.build_transform(args, options)
    except ValueError as e:
        parser.error(str(e))

    if options.DUMP_FILE:
        from pyingestion.cli.terminal_ui import run_dump_mode

        run_dump_mode(options)
    elif options.TEST_FILE:
        from pyingestion.cli.terminal_ui import run_test_mode

        run_test_mode(options, transform_stream)
    else:
        run_with_ui(options, transform_stream)



if __name__ == "__main__":
    main()
