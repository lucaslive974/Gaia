from argparse import Namespace
import os
import json

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

    def get_state_file_paths(self, input_dir: str | None = None) -> list[str]:
        paths = [os.path.join(os.getcwd(), ".gaia_resume.json")]
        if input_dir:
            paths.append(os.path.join(input_dir, ".gaia_resume.json"))
        return list(set(paths))

    def load_resume_state(self, input_dir: str | None = None) -> dict | None:
        state_paths = self.get_state_file_paths(input_dir)
        for sf_path in state_paths:
            if os.path.exists(sf_path):
                try:
                    with open(sf_path, "r", encoding="utf-8") as sf:
                        state_data = json.load(sf)
                        if input_dir:
                            if (
                                state_data.get("input_dir") == input_dir
                                and state_data.get("output_file") == self.OUTPUT_CSV
                            ):
                                return state_data
                        else:
                            return state_data
                except Exception:
                    pass
        return None

    def save_resume_state(
        self,
        input_dir: str,
        processed_files: list[str],
        successful_pages: int,
        failed_pages: int,
        total_pages: int,
    ) -> None:
        state_paths = self.get_state_file_paths(input_dir)
        state_data = {
            "input_dir": input_dir,
            "output_file": self.OUTPUT_CSV,
            "processed_files": processed_files,
            "successful_pages": successful_pages,
            "failed_pages": failed_pages,
            "total_pages": total_pages,
        }
        for sf_path in state_paths:
            try:
                with open(sf_path, "w", encoding="utf-8") as sf:
                    json.dump(state_data, sf, indent=4)
            except Exception:
                pass

    def clear_resume_state(self, input_dir: str) -> None:
        state_paths = self.get_state_file_paths(input_dir)
        for sf_path in state_paths:
            if os.path.exists(sf_path):
                try:
                    os.remove(sf_path)
                except Exception:
                    pass

    def parse_cmd_args(self, args: Namespace):
        # 1. Verify and autoload input_dir if resume is requested and it is missing
        if not getattr(args, "input_dir", None):
            if getattr(args, "resume", False):
                state = self.load_resume_state()
                if state and state.get("input_dir"):
                    args.input_dir = state.get("input_dir")
                    args.output = state.get("output_file") or args.output
                else:
                    raise ValueError(
                        "Nenhum estado de retomada encontrado no diretório atual. É necessário especificar o 'input_dir'."
                    )
            else:
                raise ValueError(
                    "o argumento posicional 'input_dir' é obrigatório a menos que --resume seja usado com um estado salvo."
                )

        # 2. Bind parsed properties
        for attr in input_attr:
            if hasattr(args, attr[0]):
                setattr(self, attr[1], getattr(args, attr[0]))


