import re
import os
import json
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")


class TransformStream(Generic[T_in, T_out]):
    input_type: type[T_in] = Any
    output_type: type[T_out] = Any

    def transform(self, data: T_in) -> T_out:
        raise NotImplementedError


class ParallelTransformStream(TransformStream[T_in, dict]):
    input_type: type[T_in] = Any
    output_type: type[dict] = dict

    def __init__(self, transforms: list[TransformStream[T_in, dict]]):
        self.transforms = transforms
        if transforms:
            self.input_type = transforms[0].input_type

    def transform(self, data: T_in) -> dict:
        result = {}
        for transform in self.transforms:
            res = transform.transform(data)
            if isinstance(res, dict):
                result.update(res)
        return result


class ChainedTransformStream(TransformStream[Any, Any]):
    def __init__(self, transforms: list[TransformStream[Any, Any]]):
        self.transforms = transforms
        if transforms:
            self.input_type = transforms[0].input_type
            self.output_type = transforms[-1].output_type

    def transform(self, data: Any) -> Any:
        current = data
        for transform in self.transforms:
            current = transform.transform(current)
        return current


class RegexEngine(TransformStream[str, dict[str, str]], ABC):
    @abstractmethod
    def parse(self, text: str) -> dict[str, str]:
        """
        Parses text sequentially using compiled patterns.
        Raises ValueError if a required pattern is not matched.
        """
        pass

    @abstractmethod
    def parse_test(self, text: str) -> tuple[dict[str, str], dict[str, bool]]:
        """
        Parses text sequentially using compiled patterns for testing/debugging.
        Does not raise ValueError, returns parsed fields and matched status.
        """
        pass


class NativeRegexEngine(RegexEngine):
    input_type = str
    output_type = dict

    def __init__(self, patterns_data: dict[str, Any]):
        self.config_file = None
        self.patterns: dict[str, dict[str, Any]] = {}
        self.load_and_validate(patterns_data)

    @property
    def regex_file_path(self):
        return self.config_file

    @regex_file_path.setter
    def regex_file_path(self, value):
        self.config_file = value

    @staticmethod
    def _detect_file_format(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".toml":
            return "toml"
        return "json"

    @staticmethod
    def _load_json(file_path: str) -> dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao parsear o arquivo JSON de regex: {e}")
        except Exception as e:
            raise ValueError(f"Erro ao ler o arquivo JSON de regex: {e}")

    @staticmethod
    def _load_toml(file_path: str) -> dict[str, Any]:
        import tomllib

        try:
            with open(file_path, "rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Erro ao parsear o arquivo TOML de regex: {e}")
        except Exception as e:
            raise ValueError(f"Erro ao ler o arquivo TOML de regex: {e}")

    @classmethod
    def from_file(cls, file_path: str | None) -> "NativeRegexEngine":
        """
        Loads regex patterns from a JSON or TOML file and instantiates the engine.
        """
        if not file_path:
            raise ValueError("O caminho do arquivo de regex deve ser fornecido.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo de regex não encontrado: {file_path}")

        fmt = cls._detect_file_format(file_path)
        if fmt == "toml":
            data = cls._load_toml(file_path)
        else:
            data = cls._load_json(file_path)

        engine = cls(data)
        engine.regex_file_path = file_path
        return engine

    def load_and_validate(self, data: dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("O JSON de regex deve ser um objeto no nível raiz.")

        patterns = {}
        for key, value in data.items():
            if not isinstance(value, dict):
                raise ValueError(
                    f"A configuração para o campo '{key}' deve ser um objeto/dicionário."
                )
            if "regex" not in value:
                raise ValueError(f"O campo '{key}' deve conter uma chave 'regex'.")
            if not isinstance(value["regex"], str):
                raise ValueError(
                    f"A chave 'regex' para o campo '{key}' deve ser uma string."
                )

            # Compile flags
            flags = 0
            if "flags" in value:
                if not isinstance(value["flags"], list):
                    raise ValueError(
                        f"A chave 'flags' para o campo '{key}' deve ser uma lista de strings."
                    )
                for flag_str in value["flags"]:
                    if not isinstance(flag_str, str):
                        raise ValueError(
                            f"As flags do campo '{key}' devem ser strings."
                        )
                    flag_val = getattr(re, flag_str.upper(), None)
                    if flag_val is None:
                        raise ValueError(
                            f"Flag de regex inválida '{flag_str}' no campo '{key}'."
                        )
                    flags |= flag_val

            try:
                compiled = re.compile(value["regex"], flags)
            except re.error as e:
                raise ValueError(f"Expressão regular inválida no campo '{key}': {e}")

            patterns[key] = {
                "regex_str": value["regex"],
                "compiled": compiled,
                "required": bool(value.get("required", False)),
                "default": str(value.get("default", "")),
                "flags": value.get("flags", []),
                "description": str(value.get("description", "")),
            }

        self.patterns = patterns

    def transform(self, data: str) -> dict[str, str]:
        return self.parse(data)

    def parse(self, text: str) -> dict[str, str]:
        results = {}
        posicao_atual = 0
        for key, entry in self.patterns.items():
            pattern = entry["compiled"]
            match = pattern.search(text, pos=posicao_atual)
            if match:
                val = (
                    match.group(1).strip() if match.groups() else match.group(0).strip()
                )
                results[key] = val
                posicao_atual = match.end()
            else:
                results[key] = entry["default"]

        for key, entry in self.patterns.items():
            if entry["required"] and not results.get(key):
                raise ValueError(f"Invalid page structure: missing {key}")

        return results

    def parse_test(self, text: str) -> tuple[dict[str, str], dict[str, bool]]:
        results = {}
        matched_status = {}
        posicao_atual = 0
        for key, entry in self.patterns.items():
            pattern = entry["compiled"]
            match = pattern.search(text, pos=posicao_atual)
            if match:
                val = (
                    match.group(1).strip() if match.groups() else match.group(0).strip()
                )
                results[key] = val
                matched_status[key] = True
                posicao_atual = match.end()
            else:
                results[key] = entry["default"]
                matched_status[key] = False

        return results, matched_status
