import unittest
import tempfile
import json
import os
from core.regex_engine import NativeRegexEngine


class TestRegexEngine(unittest.TestCase):
    def setUp(self):
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def create_temp_regex_file(self, content: dict) -> str:
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as tf:
            json.dump(content, tf)
            path = tf.name
        self.temp_files.append(path)
        return path

    def test_load_and_validate_valid_config(self):
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
        file_path = self.create_temp_regex_file(config)
        engine = NativeRegexEngine(file_path)

        self.assertEqual(engine.regex_file_path, file_path)
        self.assertIn("data_emissao", engine.patterns)
        self.assertIn("linha", engine.patterns)

        self.assertTrue(engine.patterns["data_emissao"]["required"])
        self.assertEqual(engine.patterns["data_emissao"]["default"], "01/01/2000")
        self.assertFalse(engine.patterns["linha"]["required"])
        self.assertEqual(engine.patterns["linha"]["default"], "")

    def test_load_and_validate_missing_path(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine("")

    def test_load_and_validate_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            NativeRegexEngine("/nonexistent/file.json")

    def test_load_and_validate_invalid_json(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write("{invalid json}")
            path = tf.name
        self.temp_files.append(path)
        with self.assertRaises(ValueError):
            NativeRegexEngine(path)

    def test_load_and_validate_invalid_schema_root(self):
        file_path = self.create_temp_regex_file(["not a dictionary"])
        with self.assertRaises(ValueError):
            NativeRegexEngine(file_path)

    def test_load_and_validate_invalid_field_schema(self):
        file_path = self.create_temp_regex_file({"field": "not a dictionary"})
        with self.assertRaises(ValueError):
            NativeRegexEngine(file_path)

    def test_load_and_validate_missing_regex_key(self):
        file_path = self.create_temp_regex_file({"field": {"required": True}})
        with self.assertRaises(ValueError):
            NativeRegexEngine(file_path)

    def test_load_and_validate_invalid_regex_type(self):
        file_path = self.create_temp_regex_file({"field": {"regex": 123}})
        with self.assertRaises(ValueError):
            NativeRegexEngine(file_path)

    def test_load_and_validate_invalid_flags_type(self):
        file_path = self.create_temp_regex_file(
            {"field": {"regex": "abc", "flags": "not a list"}}
        )
        with self.assertRaises(ValueError):
            NativeRegexEngine(file_path)

    def test_load_and_validate_invalid_flag_string(self):
        file_path = self.create_temp_regex_file(
            {"field": {"regex": "abc", "flags": ["INVALID_FLAG"]}}
        )
        with self.assertRaises(ValueError):
            NativeRegexEngine(file_path)

    def test_load_and_validate_invalid_regex_pattern(self):
        file_path = self.create_temp_regex_file({"field": {"regex": "["}})
        with self.assertRaises(ValueError):
            NativeRegexEngine(file_path)

    def test_parse_success(self):
        config = {
            "key1": {"regex": r"key1:\s*(\w+)", "required": True, "default": ""},
            "key2": {
                "regex": r"key2:\s*(\w+)",
                "required": False,
                "default": "missing",
            },
        }
        file_path = self.create_temp_regex_file(config)
        engine = NativeRegexEngine(file_path)

        text = "some text key1: value1 key2: value2"
        results = engine.parse(text)
        self.assertEqual(results["key1"], "value1")
        self.assertEqual(results["key2"], "value2")

    def test_parse_sequential_search_offset(self):
        config = {
            "first": {"regex": r"word:\s*(\w+)", "required": True},
            "second": {"regex": r"word:\s*(\w+)", "required": True},
        }
        file_path = self.create_temp_regex_file(config)
        engine = NativeRegexEngine(file_path)

        text = "word: apple and then word: banana"
        results = engine.parse(text)
        self.assertEqual(results["first"], "apple")
        self.assertEqual(results["second"], "banana")

    def test_parse_missing_required_raises_value_error(self):
        config = {"key1": {"regex": r"key1:\s*(\w+)", "required": True}}
        file_path = self.create_temp_regex_file(config)
        engine = NativeRegexEngine(file_path)

        text = "key2: value2"
        with self.assertRaises(ValueError):
            engine.parse(text)

    def test_parse_test_does_not_raise(self):
        config = {
            "key1": {"regex": r"key1:\s*(\w+)", "required": True},
            "key2": {"regex": r"key2:\s*(\w+)", "required": False},
        }
        file_path = self.create_temp_regex_file(config)
        engine = NativeRegexEngine(file_path)

        text = "key2: value2"
        results, matched = engine.parse_test(text)

        self.assertEqual(results["key1"], "")
        self.assertFalse(matched["key1"])
        self.assertEqual(results["key2"], "value2")
        self.assertTrue(matched["key2"])


if __name__ == "__main__":
    unittest.main()
