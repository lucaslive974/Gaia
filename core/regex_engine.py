import re
import json
import os
from abc import ABC, abstractmethod
from typing import Any


class RegexEngine(ABC):
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
    def __init__(self, regex_file_path: str):
        self.regex_file_path = regex_file_path
        self.patterns: dict[str, dict[str, Any]] = {}
        self.load_and_validate(regex_file_path)

    def load_and_validate(self, file_path: str):
        if not file_path:
            raise ValueError("O caminho do arquivo de regex deve ser fornecido.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo de regex não encontrado: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao parsear o arquivo JSON de regex: {e}")
        except Exception as e:
            raise ValueError(f"Erro ao ler o arquivo de regex: {e}")

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
                        raise ValueError(f"As flags do campo '{key}' devem ser strings.")
                    flag_val = getattr(re, flag_str.upper(), None)
                    if flag_val is None:
                        raise ValueError(
                            f"Flag de regex inválida '{flag_str}' no campo '{key}'."
                        )
                    flags |= flag_val

            try:
                compiled = re.compile(value["regex"], flags)
            except re.error as e:
                raise ValueError(
                    f"Expressão regular inválida no campo '{key}': {e}"
                )

            patterns[key] = {
                "regex_str": value["regex"],
                "compiled": compiled,
                "required": bool(value.get("required", False)),
                "default": str(value.get("default", "")),
                "flags": value.get("flags", []),
                "description": str(value.get("description", "")),
            }

        self.patterns = patterns

    def parse(self, text: str) -> dict[str, str]:
        results = {}
        posicao_atual = 0
        for key, entry in self.patterns.items():
            pattern = entry["compiled"]
            match = pattern.search(text, pos=posicao_atual)
            if match:
                val = (
                    match.group(1).strip()
                    if match.groups()
                    else match.group(0).strip()
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
                    match.group(1).strip()
                    if match.groups()
                    else match.group(0).strip()
                )
                results[key] = val
                matched_status[key] = True
                posicao_atual = match.end()
            else:
                results[key] = entry["default"]
                matched_status[key] = False

        return results, matched_status
