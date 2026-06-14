import os


class Options:
    BASE_PATH: str = ""
    OUTPUT_CSV: str = os.path.join(os.getcwd(), "output.csv")
    RESUME: bool = False
    REGEX_FILE: str | None = None
    TEST_FILE: str | None = None
    DUMP_FILE: str | None = None
    RECURSIVE: bool = False
    PAGES_PER_UNIT: int = 1
    PARSER_TYPE: str = "pdf"

    def __getitem__(self, attr):
        try:
            val = getattr(self, attr)
            return val
        except AttributeError:
            raise KeyError

    def __setitem__(self, attr, value):
        setattr(self, attr, value)

    def __contains__(self, attr):
        return hasattr(self, attr)

    def __setattr__(self, name, value):
        if name == "PAGES_PER_UNIT":
            try:
                val = int(value)
                if val < 1:
                    raise ValueError
                value = val
            except (ValueError, TypeError):
                raise ValueError(
                    "the '--pages-per-unit' argument must be an integer greater than or equal to 1."
                )
        elif name == "PARSER_TYPE":
            from pyingestion.parser import ParserType

            valid_types = [item.value for item in ParserType]
            if value not in valid_types:
                raise ValueError(f"the '--type' argument must be one of {valid_types}.")
        super().__setattr__(name, value)

    @classmethod
    def list_attr(cls) -> list[tuple[str, str]]:
        return [
            ("input_dir", "BASE_PATH"),
            ("output", "OUTPUT_CSV"),
            ("resume", "RESUME"),
            ("regex", "REGEX_FILE"),
            ("test", "TEST_FILE"),
            ("dump", "DUMP_FILE"),
            ("recursive", "RECURSIVE"),
            ("pages_per_unit", "PAGES_PER_UNIT"),
            ("type", "PARSER_TYPE"),
        ]


options = Options()
