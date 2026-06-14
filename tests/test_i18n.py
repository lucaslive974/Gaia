import os
import pytest
from unittest.mock import patch
from pyingestion.i18n import _, set_lang, get_lang, parse_lang_from_argv, Language, get_system_lang


class TestI18nLanguageSelection:
    def test_default_language_is_english(self):
        assert get_lang() == Language.EN_US
        assert _("ui_metric") == "Metric"

    def test_switch_to_portuguese(self):
        set_lang("pt")
        assert get_lang() == Language.PT_BR
        assert _("ui_metric") == "Métrica"

        set_lang(Language.EN_US)
        assert get_lang() == Language.EN_US

    def test_invalid_language_does_not_switch(self):
        set_lang("invalid_lang")
        assert get_lang() == Language.EN_US
        assert _("ui_metric") == "Metric"


class TestI18nTranslation:
    @pytest.mark.parametrize("lang, expected", [
        ("en", "The input directory '/some/dir' does not exist."),
        ("pt", "O diretório de entrada '/some/dir' não existe."),
    ])
    def test_format_parameters(self, lang, expected):
        set_lang(lang)
        assert _("err_dir_not_exist", base_path="/some/dir") == expected

    def test_fallback_on_missing_key(self):
        assert _("non_existent_key_abc") == "non_existent_key_abc"


class TestI18nAutoDetection:
    @pytest.mark.parametrize("argv, system_lang, expected", [
        ([], Language.EN_US, "en"),
        (["main.py"], Language.EN_US, "en"),
        (["main.py", "--lang", "pt"], Language.EN_US, "pt"),
        (["main.py", "-l", "pt"], Language.EN_US, "pt"),
        (["main.py", "--lang", "en"], Language.EN_US, "en"),
        (["main.py", "-l", "fr"], Language.EN_US, "en"),
        (["main.py", "--lang"], Language.EN_US, "en"),
        ([], Language.PT_BR, "pt"),
        (["main.py"], Language.PT_BR, "pt"),
        (["main.py", "--lang", "en"], Language.PT_BR, "en"),
    ])
    def test_parse_lang_from_argv_scenarios(self, argv, system_lang, expected):
        with patch("pyingestion.i18n.get_system_lang", return_value=system_lang):
            assert parse_lang_from_argv(argv) == expected

    @pytest.mark.parametrize("locale_val, expected", [
        (("pt_BR", "UTF-8"), Language.PT_BR),
        (("en_US", "UTF-8"), Language.EN_US),
    ])
    def test_get_system_lang_from_locale(self, locale_val, expected):
        with patch("locale.getlocale", return_value=locale_val):
            assert get_system_lang() == expected

    @pytest.mark.parametrize("env_dict, expected", [
        ({"LANG": "pt_PT.UTF-8"}, Language.PT_BR),
        ({"LANG": "en_GB.UTF-8"}, Language.EN_US),
        ({}, Language.EN_US),
    ])
    def test_get_system_lang_from_env_fallback(self, env_dict, expected):
        with patch("locale.getlocale", return_value=(None, None)):
            with patch.dict(os.environ, env_dict, clear=True if not env_dict else False):
                assert get_system_lang() == expected
