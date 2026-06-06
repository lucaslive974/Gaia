import unittest
from gaia.i18n import _, set_lang, get_lang


class TestI18n(unittest.TestCase):
    def setUp(self):
        # Reset to default language before each test
        set_lang("en")

    def test_default_language_is_english(self):
        self.assertEqual(get_lang(), "en")
        self.assertEqual(_("ui_metric"), "Metric")

    def test_switch_to_portuguese(self):
        set_lang("pt")
        self.assertEqual(get_lang(), "pt")
        self.assertEqual(_("ui_metric"), "Métrica")

    def test_format_parameters(self):
        # English formatting
        self.assertEqual(
            _("err_dir_not_exist", base_path="/some/dir"),
            "The input directory '/some/dir' does not exist."
        )

        # Portuguese formatting
        set_lang("pt")
        self.assertEqual(
            _("err_dir_not_exist", base_path="/some/dir"),
            "O diretório de entrada '/some/dir' não existe."
        )

    def test_fallback_on_missing_key(self):
        # If key does not exist, it should return the key itself
        self.assertEqual(_("non_existent_key_abc"), "non_existent_key_abc")

    def test_invalid_language_does_not_switch(self):
        set_lang("invalid_lang")
        # Should stay at "en"
        self.assertEqual(get_lang(), "en")
        self.assertEqual(_("ui_metric"), "Metric")


if __name__ == "__main__":
    unittest.main()
