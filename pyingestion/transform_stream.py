import json
import os
import re
from abc import ABC, abstractmethod
from typing import Generic, TypedDict, TypeVar, cast

T_in = TypeVar("T_in", contravariant=True)
T_out = TypeVar("T_out", covariant=True)


class PatternConfig(TypedDict):
    regex_str: str
    compiled: re.Pattern[str]
    required: bool
    default: str
    flags: list[str]
    description: str


class TransformStream(Generic[T_in, T_out]):
    input_type: type[T_in] = cast(type[T_in], object)
    output_type: type[T_out] = cast(type[T_out], object)

    def transform(self, data: T_in) -> T_out:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError


class ParallelTransformStream(TransformStream[T_in, dict[str, object]]):
    input_type: type[T_in] = cast(type[T_in], object)
    output_type: type[dict[str, object]] = cast(type[dict[str, object]], dict)

    def __init__(self, transforms: list[TransformStream[T_in, dict[str, object]]]):
        self.transforms = transforms
        if transforms:
            self.input_type = transforms[0].input_type

    def transform(self, data: T_in) -> dict[str, object]:
        result: dict[str, object] = {}
        for transform in self.transforms:
            res = transform.transform(data)
            if isinstance(res, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                result.update(res)
        return result


class ChainedTransformStream(TransformStream[object, object]):
    def __init__(self, transforms: list[TransformStream[object, object]]):
        self.transforms = transforms
        if transforms:
            self.input_type = transforms[0].input_type
            self.output_type = transforms[-1].output_type

    def transform(self, data: object) -> object:
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

    @abstractmethod
    def parse_test(self, text: str) -> tuple[dict[str, str], dict[str, bool]]:
        """
        Parses text sequentially using compiled patterns for testing/debugging.
        Does not raise ValueError, returns parsed fields and matched status.
        """


class NativeRegexEngine(RegexEngine):
    input_type = str
    output_type = cast(type[dict[str, str]], dict)

    def __init__(self, patterns_data: dict[str, object]):
        self.config_file = None
        self.patterns: dict[str, PatternConfig] = {}
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
    def _load_json(file_path: str) -> dict[str, object]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return cast(dict[str, object], json.load(f))
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao parsear o arquivo JSON de regex: {e}")
        except Exception as e:
            raise ValueError(f"Erro ao ler o arquivo JSON de regex: {e}")

    @staticmethod
    def _load_toml(file_path: str) -> dict[str, object]:
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

    def load_and_validate(self, data: dict[str, object]):
        if not isinstance(data, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("O JSON de regex deve ser um objeto no nível raiz.")  # pyright: ignore[reportUnreachable]

        patterns: dict[str, PatternConfig] = {}
        for key, value in data.items():
            if not isinstance(value, dict):
                raise ValueError(
                    f"A configuração para o campo '{key}' deve ser um objeto/dicionário."
                )
            val_dict = cast(dict[str, object], value)
            if "regex" not in val_dict:
                raise ValueError(f"O campo '{key}' deve conter uma chave 'regex'.")
            if not isinstance(val_dict["regex"], str):
                raise ValueError(
                    f"A chave 'regex' para o campo '{key}' deve ser uma string."
                )

            # Compile flags
            flags = 0
            flags_list: list[str] = []
            if "flags" in val_dict:
                raw_flags = val_dict["flags"]
                if not isinstance(raw_flags, list):
                    raise ValueError(
                        f"A chave 'flags' para o campo '{key}' deve ser uma lista de strings."
                    )
                for flag_str in raw_flags:
                    if not isinstance(flag_str, str):
                        raise ValueError(
                            f"As flags do campo '{key}' devem ser strings."
                        )
                    flag_val = getattr(re, flag_str.upper(), None)
                    if not isinstance(flag_val, int):
                        raise ValueError(
                            f"Flag de regex inválida '{flag_str}' no campo '{key}'."
                        )
                    flags |= flag_val
                    flags_list.append(flag_str)

            try:
                compiled = re.compile(val_dict["regex"], flags)
            except re.error as e:
                raise ValueError(f"Expressão regular inválida no campo '{key}': {e}")

            patterns[key] = {
                "regex_str": val_dict["regex"],
                "compiled": compiled,
                "required": bool(val_dict.get("required", False)),
                "default": str(val_dict.get("default", "")),
                "flags": flags_list,
                "description": str(val_dict.get("description", "")),
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


from collections.abc import Callable, Mapping
from enum import Enum
from typing import Any


class TransformStreamType(Enum):
    REGEX = "regex"
    EMBED = "embed"
    EMBED_TRANSFORM = "embed-transform"


class TransformStreamFactory:
    _CREATORS: dict[
        str, Callable[[Mapping[str, object]], TransformStream[Any, Any]]  # pyright: ignore[reportExplicitAny]
    ] = {}

    @classmethod
    def register(
        cls,
        type_name: str,
        creator: Callable[[Mapping[str, object]], TransformStream[Any, Any]],  # pyright: ignore[reportExplicitAny]
    ) -> None:
        cls._CREATORS[type_name] = creator

    @staticmethod
    def create(
        transform_type: str | TransformStreamType,
        config: Mapping[str, object] | None = None,
    ) -> TransformStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
        pt = (
            transform_type.value
            if isinstance(transform_type, TransformStreamType)
            else transform_type.lower()
        )

        cfg = config or {}
        if pt == "regex":
            rules_file = str(cfg.get("config_file") or cfg.get("rules_file") or "")
            if not rules_file:
                raise ValueError(
                    "Transform of type 'regex' requires 'config_file' or 'rules_file'."
                )
            return NativeRegexEngine.from_file(rules_file)
        elif pt in ("embed", "embed-transform"):
            creator = TransformStreamFactory._CREATORS.get(pt)
            if not creator:
                raise ValueError(f"Transform type '{pt}' is not registered.")
            return creator(cfg)
        else:
            raise ValueError(f"Unknown transform type: {pt}")
