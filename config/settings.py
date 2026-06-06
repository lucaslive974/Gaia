from argparse import Namespace
import os

input_attr = [
    ["input_dir", "BASE_PATH"],
    ["output", "OUTPUT_CSV"],
    ["resume", "RESUME"],
]


class Settings:
    BASE_PATH: str = ""
    OUTPUT_CSV: str = os.path.join(os.getcwd(), "output.csv")
    RESUME: bool = False

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

    def parse_cmd_args(self, args: Namespace):
        for attr in input_attr:
            if hasattr(args, attr[0]):
                setattr(self, attr[1], getattr(args, attr[0]))

