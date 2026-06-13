import pytest
from pydocstruct.i18n import _, set_lang, get_lang


@pytest.fixture(autouse=True)
def reset_lang():
    # Reset to default language before each test
    set_lang("en")


def test_default_language_is_english():
    assert get_lang() == "en"
    assert _("ui_metric") == "Metric"


def test_switch_to_portuguese():
    set_lang("pt")
    assert get_lang() == "pt"
    assert _("ui_metric") == "Métrica"


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
    assert get_lang() == "en"
    assert _("ui_metric") == "Metric"
