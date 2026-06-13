import os
from argparse import Namespace
from pydocstructurer.options import Options
from pydocstructurer.extraction_session import ExtractionSession
from pydocstructurer.i18n import _, set_lang


class CliHelper:
    @classmethod
    def parse_and_build_options(cls, args: Namespace) -> Options:
        options = Options()

        # 0. Set and validate language first so errors are translated
        lang = getattr(args, "lang", None)
        if isinstance(lang, str):
            if lang not in ("en", "pt"):
                raise ValueError(_("err_lang_invalid"))
            set_lang(lang)
            options.LANG = lang

        is_test = getattr(args, "test", None) is not None
        is_dump = getattr(args, "dump", None) is not None
        # 1. Verify and autoload input_dir if resume is requested and it is missing
        if not getattr(args, "input_dir", None) and not is_test and not is_dump:
            if getattr(args, "resume", False):
                state = ExtractionSession.load_state()
                if state and state.get("input_dir"):
                    args.input_dir = state.get("input_dir")
                    args.output = state.get("output_file") or args.output
                    args.regex = state.get("regex_file") or getattr(args, "regex", None)
                else:
                    raise ValueError(_("err_resume_no_state"))
            else:
                raise ValueError(_("err_input_dir_required"))

        # 2. Check for required regex file if not resuming and not in dump mode
        if not is_dump:
            if not getattr(args, "resume", False):
                if not getattr(args, "regex", None):
                    raise ValueError(_("err_regex_required_normal"))
            else:
                # If resuming, load state to autoload regex if not explicitly passed
                state = ExtractionSession.load_state(getattr(args, "input_dir", None))
                if state and state.get("regex_file"):
                    args.regex = getattr(args, "regex", None) or state.get("regex_file")

                # Still, we must have a regex file to resume
                if not getattr(args, "regex", None):
                    raise ValueError(_("err_regex_required_resume"))

        # 3. Check pages_per_unit validation
        pages_per_unit = getattr(args, "pages_per_unit", None)
        if pages_per_unit is not None:
            try:
                ppu_val = int(pages_per_unit)
                if ppu_val < 1:
                    raise ValueError
            except (ValueError, TypeError):
                raise ValueError(_("err_ppu_invalid"))

        # 4. Bind parsed properties
        for attr in Options.list_attr():
            if hasattr(args, attr[0]):
                val = getattr(args, attr[0])
                if val is not None:
                    setattr(options, attr[1], val)

        return options
