import pytesseract
from abc import ABC, abstractmethod
from config import settings

from typing import Any

class CnnAiModel(ABC):
    @abstractmethod
    def process_image(self, image: Any) -> str:
        pass


class Pytesseract(CnnAiModel):
    _language = 'por'

    def __init__(self):
        self._ocr_pytesseract_config = f'--oem 1 --psm 6 --tessdata-dir {settings["TRAINED_DATA_DIR"]}'

    def process_image(self, image: Any) -> str:
        result = pytesseract.image_to_string(image, lang=self._language, config=self._ocr_pytesseract_config)
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return str(result)
