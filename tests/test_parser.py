import unittest
from unittest.mock import MagicMock
from gaia import DefaultOcrParser, ExtractionSession


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

        session = ExtractionSession(mock_observer)

        # Execute generator and consume it
        pages = list(parser.process_file("/dummy/file.pdf", session=session))

        mock_observer.on_page_start.assert_called_once_with(1, 1)
        mock_observer.on_page_processed.assert_called_once_with(True, 1, 0, 1, 1)

        self.assertEqual(len(pages), 1)
        written_dict = pages[0]
        self.assertEqual(written_dict["data_emissao"], "10/10/2026")
        self.assertEqual(written_dict["data_vencimento"], "10/11/2026")
        self.assertEqual(written_dict["n_infracao"], "ABC1234")
        self.assertEqual(written_dict["valor"], "150,00")

    def test_parser_orchestration_multi_page_units(self):
        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 2

        page1_text = "Data de Emissao 10/10/2026\n"
        page2_text = "N Auto de Infracao ABC1234\n"
        mock_extractor.extract_pages.return_value = iter([page1_text, page2_text])

        mock_regex = MagicMock()
        mock_regex.parse.return_value = {
            "data_emissao": "10/10/2026",
            "n_infracao": "ABC1234",
        }

        parser = DefaultOcrParser(
            extractor=mock_extractor, regex_engine=mock_regex
        )

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        session = ExtractionSession(mock_observer)

        # Execute generator and consume it
        pages = list(parser.process_file("/dummy/file.pdf", session=session, pages_per_unit=2))

        # Verify that pages were combined and parse was called with the combined text
        mock_regex.parse.assert_called_once_with(f"{page1_text}\n{page2_text}")

        # Observer is notified once for the combined unit (index 1, total 1)
        mock_observer.on_page_start.assert_called_once_with(1, 1)
        mock_observer.on_page_processed.assert_called_once_with(True, 1, 0, 1, 1)

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["data_emissao"], "10/10/2026")
        self.assertEqual(pages[0]["n_infracao"], "ABC1234")

    def test_parser_cancellation_mid_file(self):
        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 3
        mock_extractor.extract_pages.return_value = iter(["page 1", "page 2", "page 3"])

        mock_regex = MagicMock()
        mock_regex.parse.return_value = {"field": "value"}

        parser = DefaultOcrParser(
            extractor=mock_extractor, regex_engine=mock_regex
        )

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        # Simulate cancellation during on_page_start
        def on_page_start_side_effect(page_index, total_pages):
            if page_index == 1:
                mock_observer.is_cancelled = True

        mock_observer.on_page_start.side_effect = on_page_start_side_effect

        session = ExtractionSession(mock_observer)

        pages = list(parser.process_file("/dummy/file.pdf", session=session))

        # Only the first page should have been processed before cancellation took effect
        self.assertEqual(len(pages), 1)
        self.assertTrue(session.is_cancelled)
        mock_regex.parse.assert_called_once_with("page 1")

    def test_parser_programmatic_import_and_parameterless_session(self):
        # Verify that we can import public symbols directly from 'gaia' package
        from gaia import (
            DefaultOcrParser,
            NoOpExtractionSession
        )

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text page"])

        mock_regex = MagicMock()
        mock_regex.parse.return_value = {"field": "value"}

        # Instantiate without importing modules internally
        parser = DefaultOcrParser(
            extractor=mock_extractor, regex_engine=mock_regex
        )

        # Execute process_file without passing the session parameter
        pages = list(parser.process_file("/dummy/file.pdf"))

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["field"], "value")
        mock_regex.parse.assert_called_once_with("valid text page")


if __name__ == "__main__":
    unittest.main()
