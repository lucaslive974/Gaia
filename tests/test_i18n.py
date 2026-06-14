import os
import pytest
from unittest.mock import patch
from pydocstructurer.i18n import _, set_lang, get_lang, parse_lang_from_argv, Language, get_system_lang


@pytest.fixture(autouse=True)
def reset_lang():
    # Reset to default language before each test
    set_lang(Language.EN_US)


def test_default_language_is_english():
    assert get_lang() == Language.EN_US
    assert _("ui_metric") == "Metric"


def test_switch_to_portuguese():
    set_lang("pt")
    assert get_lang() == Language.PT_BR
    assert _("ui_metric") == "Métrica"

    set_lang(Language.EN_US)
    assert get_lang() == Language.EN_US


def test_format_parameters():
    # English formatting
    assert (
        _("err_dir_not_exist", base_path="/some/dir")
        == "The input directory '/some/dir' does not exist."
    )

    # Portuguese formatting
    set_lang("pt")
    assert (
        _("err_dir_not_exist", base_path="/some/dir")
        == "O diretório de entrada '/some/dir' não existe."
    )


def test_fallback_on_missing_key():
    # If key does not exist, it should return the key itself
    assert _("non_existent_key_abc") == "non_existent_key_abc"


def test_invalid_language_does_not_switch():
    set_lang("invalid_lang")
    # Should stay at "en"
    assert get_lang() == Language.EN_US
    assert _("ui_metric") == "Metric"


def test_parse_lang_from_argv():
    # With default system lang mocked to EN_US
    with patch("pydocstructurer.i18n.get_system_lang", return_value=Language.EN_US):
        assert parse_lang_from_argv([]) == "en"
        assert parse_lang_from_argv(["main.py"]) == "en"
        assert parse_lang_from_argv(["main.py", "--lang", "pt"]) == "pt"
        assert parse_lang_from_argv(["main.py", "-l", "pt"]) == "pt"
        assert parse_lang_from_argv(["main.py", "--lang", "en"]) == "en"
        assert parse_lang_from_argv(["main.py", "-l", "fr"]) == "en"
        assert parse_lang_from_argv(["main.py", "--lang"]) == "en"

    # With default system lang mocked to PT_BR
    with patch("pydocstructurer.i18n.get_system_lang", return_value=Language.PT_BR):
        assert parse_lang_from_argv([]) == "pt"
        assert parse_lang_from_argv(["main.py"]) == "pt"
        assert parse_lang_from_argv(["main.py", "--lang", "en"]) == "en"


def test_get_system_lang_locale():
    with patch("locale.getlocale", return_value=("pt_BR", "UTF-8")):
        assert get_system_lang() == Language.PT_BR

    with patch("locale.getlocale", return_value=("en_US", "UTF-8")):
        assert get_system_lang() == Language.EN_US

    with patch("locale.getlocale", return_value=(None, None)):
        # locale is None, fallback to env variables
        with patch.dict(os.environ, {"LANG": "pt_PT.UTF-8"}):
            assert get_system_lang() == Language.PT_BR

        with patch.dict(os.environ, {"LANG": "en_GB.UTF-8"}):
            assert get_system_lang() == Language.EN_US

        with patch.dict(os.environ, {}, clear=True):
            assert get_system_lang() == Language.EN_US
