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

        parser = DefaultOcrParser(extractor=mock_extractor)

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        session = ExtractionSession(mock_observer)

        # Execute generator and consume it
        pages = list(parser.process_file("/dummy/file.pdf", session=session))

        self.assertEqual(len(pages), 1)
        unit_index, total_units, raw_text = pages[0]
        self.assertEqual(unit_index, 1)
        self.assertEqual(total_units, 1)
        self.assertEqual(raw_text, valid_text)
        self.assertEqual(session.total_pages, 1)

    def test_parser_orchestration_multi_page_units(self):
        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 2

        page1_text = "Data de Emissao 10/10/2026\n"
        page2_text = "N Auto de Infracao ABC1234\n"
        mock_extractor.extract_pages.return_value = iter([page1_text, page2_text])

        parser = DefaultOcrParser(extractor=mock_extractor)

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        session = ExtractionSession(mock_observer)

        # Execute generator and consume it
        pages = list(parser.process_file("/dummy/file.pdf", session=session, pages_per_unit=2))

        self.assertEqual(len(pages), 1)
        unit_index, total_units, raw_text = pages[0]
        self.assertEqual(unit_index, 1)
        self.assertEqual(total_units, 1)
        self.assertEqual(raw_text, f"{page1_text}\n{page2_text}")
        self.assertEqual(session.total_pages, 2)

    def test_parser_cancellation_mid_file(self):
        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 3
        mock_extractor.extract_pages.return_value = iter(["page 1", "page 2", "page 3"])

        parser = DefaultOcrParser(extractor=mock_extractor)

        mock_observer = MagicMock()
        mock_observer.is_cancelled = False

        session = ExtractionSession(mock_observer)

        # Consume first element, then cancel session
        gen = parser.process_file("/dummy/file.pdf", session=session)
        
        first_page = next(gen)
        self.assertEqual(first_page[2], "page 1")
        
        session.is_cancelled = True
        
        # Generator should stop yielding immediately
        pages_after_cancel = list(gen)
        self.assertEqual(len(pages_after_cancel), 0)

    def test_parser_programmatic_import_and_parameterless_session(self):
        # Verify that we can import public symbols directly from 'gaia' package
        from gaia import (
            DefaultOcrParser,
            NoOpExtractionSession
        )

        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        mock_extractor.extract_pages.return_value = iter(["valid text page"])

        # Instantiate without importing modules internally
        parser = DefaultOcrParser(extractor=mock_extractor)

        # Execute process_file without passing the session parameter
        pages = list(parser.process_file("/dummy/file.pdf"))

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0][2], "valid text page")


if __name__ == "__main__":
    unittest.main()
