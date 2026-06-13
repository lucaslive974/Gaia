import json
import os
import pytest
from pydocstructurer import NativeRegexEngine


@pytest.fixture
def create_temp_regex_file(tmp_path):
    def _create(content: dict) -> str:
        file_path = os.path.join(tmp_path, "rules.json")
        with open(file_path, "w", encoding="utf-8") as tf:
            json.dump(content, tf)
        return file_path

    return _create


def test_load_and_validate_valid_config_from_file(create_temp_regex_file):
    config = {
        "data_emissao": {
            "regex": r"Data\s+de\s+Emiss[ãa]o\s+(\d{2}/\d{2}/\d{4})",
            "flags": ["IGNORECASE", "VERBOSE"],
            "required": True,
            "default": "01/01/2000",
        },
        "linha": {
            "regex": r"Linha:\s+(\d+)",
            "flags": ["IGNORECASE"],
            "required": False,
            "default": "",
        },
    }
    file_path = create_temp_regex_file(config)
    engine = NativeRegexEngine.from_file(file_path)

    assert engine.regex_file_path == file_path
    assert "data_emissao" in engine.patterns
    assert "linha" in engine.patterns

    assert engine.patterns["data_emissao"]["required"] is True
    assert engine.patterns["data_emissao"]["default"] == "01/01/2000"
    assert engine.patterns["linha"]["required"] is False
    assert engine.patterns["linha"]["default"] == ""


def test_instantiation_with_in_memory_dict():
    config = {
        "key1": {"regex": r"key1:\s*(\w+)", "required": True, "default": ""},
    }
    engine = NativeRegexEngine(config)
    assert engine.regex_file_path is None
    assert "key1" in engine.patterns

    text = "key1: value1"
    results = engine.parse(text)
    assert results["key1"] == "value1"


def test_load_and_validate_missing_path():
    with pytest.raises(ValueError):
        NativeRegexEngine.from_file("")


def test_load_and_validate_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        NativeRegexEngine.from_file("/nonexistent/file.json")


def test_load_and_validate_invalid_json(tmp_path):
    file_path = os.path.join(tmp_path, "invalid.json")
    with open(file_path, "w", encoding="utf-8") as tf:
        tf.write("{invalid json}")
    with pytest.raises(ValueError):
        NativeRegexEngine.from_file(file_path)


def test_load_and_validate_invalid_schema_root():
    with pytest.raises(ValueError):
        NativeRegexEngine(["not a dictionary"])


def test_load_and_validate_invalid_field_schema():
    with pytest.raises(ValueError):
        NativeRegexEngine({"field": "not a dictionary"})


def test_load_and_validate_missing_regex_key():
    with pytest.raises(ValueError):
        NativeRegexEngine({"field": {"required": True}})


def test_load_and_validate_invalid_regex_type():
    with pytest.raises(ValueError):
        NativeRegexEngine({"field": {"regex": 123}})


def test_load_and_validate_invalid_flags_type():
    with pytest.raises(ValueError):
        NativeRegexEngine({"field": {"regex": "abc", "flags": "not a list"}})


def test_load_and_validate_invalid_flag_string():
    with pytest.raises(ValueError):
        NativeRegexEngine({"field": {"regex": "abc", "flags": ["INVALID_FLAG"]}})


def test_load_and_validate_invalid_regex_pattern():
    with pytest.raises(ValueError):
        NativeRegexEngine({"field": {"regex": "["}})


def test_parse_success():
    config = {
        "key1": {"regex": r"key1:\s*(\w+)", "required": True, "default": ""},
        "key2": {
            "regex": r"key2:\s*(\w+)",
            "required": False,
            "default": "missing",
        },
    }
    engine = NativeRegexEngine(config)

    text = "some text key1: value1 key2: value2"
    results = engine.parse(text)
    assert results["key1"] == "value1"
    assert results["key2"] == "value2"


def test_parse_sequential_search_offset():
    config = {
        "first": {"regex": r"word:\s*(\w+)", "required": True},
        "second": {"regex": r"word:\s*(\w+)", "required": True},
    }
    engine = NativeRegexEngine(config)

    text = "word: apple and then word: banana"
    results = engine.parse(text)
    assert results["first"] == "apple"
    assert results["second"] == "banana"


def test_parse_missing_required_raises_value_error():
    config = {"key1": {"regex": r"key1:\s*(\w+)", "required": True}}
    engine = NativeRegexEngine(config)

    text = "key2: value2"
    with pytest.raises(ValueError):
        engine.parse(text)


def test_parse_test_does_not_raise():
    config = {
        "key1": {"regex": r"key1:\s*(\w+)", "required": True},
        "key2": {"regex": r"key2:\s*(\w+)", "required": False},
    }
    engine = NativeRegexEngine(config)

    text = "key2: value2"
    results, matched = engine.parse_test(text)

    assert results["key1"] == ""
    assert matched["key1"] is False
    assert results["key2"] == "value2"
    assert matched["key2"] is True


def test_detect_file_format():
    assert NativeRegexEngine._detect_file_format("rules.json") == "json"
    assert NativeRegexEngine._detect_file_format("rules.toml") == "toml"
    assert NativeRegexEngine._detect_file_format("rules.TOML") == "toml"
    assert NativeRegexEngine._detect_file_format("rules.txt") == "json"


def test_load_and_validate_valid_toml_config_from_file(tmp_path):
    # Write valid TOML config
    toml_content = """
    [infraction_id]
    regex = 'Código da Infração:\\s*([A-Za-z0-9-]+)'
    required = true
    default = 'N/A'

    [plate]
    regex = 'Placa:\\s*([A-Z]{3}-\\d[A-Z0-9]\\d{2})'
    required = true
    """
    file_path = os.path.join(tmp_path, "rules.toml")
    with open(file_path, "w", encoding="utf-8") as tf:
        tf.write(toml_content)

    engine = NativeRegexEngine.from_file(file_path)
    assert engine.regex_file_path == file_path
    assert "infraction_id" in engine.patterns
    assert "plate" in engine.patterns
    assert engine.patterns["infraction_id"]["required"] is True
    assert engine.patterns["infraction_id"]["default"] == "N/A"

    text = "Código da Infração: ABC-123\nPlaca: XYZ-9876"
    results = engine.parse(text)
    assert results["infraction_id"] == "ABC-123"
    assert results["plate"] == "XYZ-9876"


def test_load_and_validate_invalid_toml(tmp_path):
    # Write invalid TOML (missing closing bracket/quote)
    toml_content = """
    [infraction_id
    regex = 'unclosed
    """
    file_path = os.path.join(tmp_path, "invalid.toml")
    with open(file_path, "w", encoding="utf-8") as tf:
        tf.write(toml_content)

    with pytest.raises(ValueError) as excinfo:
        NativeRegexEngine.from_file(file_path)
    assert "Erro ao parsear o arquivo TOML de regex" in str(excinfo.value)
