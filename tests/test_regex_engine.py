import unittest
import tempfile
import json
import os
from gaia import NativeRegexEngine


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

    def test_load_and_validate_valid_config_from_file(self):
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
        engine = NativeRegexEngine.from_file(file_path)

        self.assertEqual(engine.regex_file_path, file_path)
        self.assertIn("data_emissao", engine.patterns)
        self.assertIn("linha", engine.patterns)

        self.assertTrue(engine.patterns["data_emissao"]["required"])
        self.assertEqual(engine.patterns["data_emissao"]["default"], "01/01/2000")
        self.assertFalse(engine.patterns["linha"]["required"])
        self.assertEqual(engine.patterns["linha"]["default"], "")

    def test_instantiation_with_in_memory_dict(self):
        config = {
            "key1": {"regex": r"key1:\s*(\w+)", "required": True, "default": ""},
        }
        engine = NativeRegexEngine(config)
        self.assertIsNone(engine.regex_file_path)
        self.assertIn("key1", engine.patterns)
        
        text = "key1: value1"
        results = engine.parse(text)
        self.assertEqual(results["key1"], "value1")

    def test_load_and_validate_missing_path(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine.from_file("")

    def test_load_and_validate_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            NativeRegexEngine.from_file("/nonexistent/file.json")

    def test_load_and_validate_invalid_json(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write("{invalid json}")
            path = tf.name
        self.temp_files.append(path)
        with self.assertRaises(ValueError):
            NativeRegexEngine.from_file(path)

    def test_load_and_validate_invalid_schema_root(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine(["not a dictionary"])

    def test_load_and_validate_invalid_field_schema(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine({"field": "not a dictionary"})

    def test_load_and_validate_missing_regex_key(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine({"field": {"required": True}})

    def test_load_and_validate_invalid_regex_type(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine({"field": {"regex": 123}})

    def test_load_and_validate_invalid_flags_type(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine({"field": {"regex": "abc", "flags": "not a list"}})

    def test_load_and_validate_invalid_flag_string(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine({"field": {"regex": "abc", "flags": ["INVALID_FLAG"]}})

    def test_load_and_validate_invalid_regex_pattern(self):
        with self.assertRaises(ValueError):
            NativeRegexEngine({"field": {"regex": "["}})

    def test_parse_success(self):
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
        self.assertEqual(results["key1"], "value1")
        self.assertEqual(results["key2"], "value2")

    def test_parse_sequential_search_offset(self):
        config = {
            "first": {"regex": r"word:\s*(\w+)", "required": True},
            "second": {"regex": r"word:\s*(\w+)", "required": True},
        }
        engine = NativeRegexEngine(config)

        text = "word: apple and then word: banana"
        results = engine.parse(text)
        self.assertEqual(results["first"], "apple")
        self.assertEqual(results["second"], "banana")

    def test_parse_missing_required_raises_value_error(self):
        config = {"key1": {"regex": r"key1:\s*(\w+)", "required": True}}
        engine = NativeRegexEngine(config)

        text = "key2: value2"
        with self.assertRaises(ValueError):
            engine.parse(text)

    def test_parse_test_does_not_raise(self):
        config = {
            "key1": {"regex": r"key1:\s*(\w+)", "required": True},
            "key2": {"regex": r"key2:\s*(\w+)", "required": False},
        }
        engine = NativeRegexEngine(config)

        text = "key2: value2"
        results, matched = engine.parse_test(text)

        self.assertEqual(results["key1"], "")
        self.assertFalse(matched["key1"])
        self.assertEqual(results["key2"], "value2")
        self.assertTrue(matched["key2"])


if __name__ == "__main__":
    unittest.main()
