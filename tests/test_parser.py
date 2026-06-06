import unittest
from unittest.mock import MagicMock
from core.ocr_parser import DefaultOcrParser


class TestParser(unittest.TestCase):
    def test_parser_orchestration(self):
        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1

        valid_text = (
            "Data de Emissao 10/10/2026\n"
            "Data do Vencimento 10/11/2026\n"
            "N Auto de Infracao ABC1234\n"
            "Valor: R$ 150,00"
        )
        mock_extractor.extract_pages.return_value = iter([valid_text])

        mock_regex = MagicMock()
        mock_regex.parse.return_value = {
            "data_emissao": "10/10/2026",
            "data_vencimento": "10/11/2026",
            "n_infracao": "ABC1234",
            "valor": "150,00",
        }

        parser = DefaultOcrParser(
            extractor=mock_extractor, regex_engine=mock_regex
        )

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Execute generator and consume it
        pages = list(parser.process_file("/dummy/file.pdf", observer=mock_observer))

        mock_observer.on_page_start.assert_called_once_with(1, 1)
        mock_observer.on_page_processed.assert_called_once_with(True, 1, 0, 1, 1)

        self.assertEqual(len(pages), 1)
        written_dict = pages[0]
        # Verify returned keys match JSON config directly (no legacy key map)
        self.assertEqual(written_dict["data_emissao"], "10/10/2026")
        self.assertEqual(written_dict["data_vencimento"], "10/11/2026")
        self.assertEqual(written_dict["n_infracao"], "ABC1234")
        self.assertEqual(written_dict["valor"], "150,00")


if __name__ == "__main__":
    unittest.main()
