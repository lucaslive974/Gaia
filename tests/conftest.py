import pytest
import json
from pydocstructurer.options import Options
from pydocstructurer.i18n import set_lang, Language


@pytest.fixture
def fresh_options():
    """Returns a fresh instance of the Options class."""
    return Options()


@pytest.fixture(autouse=True)
def reset_lang():
    """Automatically resets the translation language to English before each test."""
    set_lang(Language.EN_US)


@pytest.fixture
def temp_file_factory(tmp_path):
    """Factory fixture to create temporary files with text or JSON content."""

    def _create_file(filename: str, content: str | dict, is_json: bool = False) -> str:
        file_path = tmp_path / filename
        if is_json:
            file_path.write_text(json.dumps(content), encoding="utf-8")
        else:
            file_path.write_text(content, encoding="utf-8")
        return str(file_path)

    return _create_file
