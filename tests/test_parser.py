import unittest
from unittest.mock import MagicMock, patch
from core.ocr_parser import DefaultOcrParser


class TestParser(unittest.TestCase):
    @patch("core.ocr_parser.listdir")
    @patch("core.ocr_parser.path.exists")
    def test_parser_orchestration(self, mock_exists, mock_listdir):
        mock_exists.return_value = True
        mock_listdir.return_value = ["file1.pdf"]
        
        mock_extractor = MagicMock()
        mock_extractor.get_page_count.return_value = 1
        
        # Text matching DefaultOcrParser._RE_KVP
        valid_text = (
            "Data de Emissao 10/10/2026\n"
            "Data do Vencimento 10/11/2026\n"
            "N Auto de Infracao ABC1234\n"
            "Valor: R$ 150,00"
        )
        mock_extractor.extract_pages.return_value = iter([valid_text])
        
        mock_writer = MagicMock()
        
        parser = DefaultOcrParser(extractor=mock_extractor, csv_writer=mock_writer)
        
        mock_observer = MagicMock()
        mock_observer.is_cancelled = False
        parser.process("/dummy/dir", observer=mock_observer)
        
        mock_observer.on_start.assert_called_once_with(1)
        mock_observer.on_file_start.assert_called_once()
        mock_observer.on_page_start.assert_called_once_with(1, 1)
        mock_observer.on_page_processed.assert_called_once_with(True, 1, 0, 1, 1)

        mock_observer.on_file_complete.assert_called_once_with(1, 100.0)
        mock_observer.on_complete.assert_called_once_with(1, 1)
        
        # Verify parsed dict output structure
        mock_writer.write.assert_called_once()
        written_dict = mock_writer.write.call_args[0][0]
        self.assertEqual(written_dict["DAT_EMISS"], "10/10/2026")
        self.assertEqual(written_dict["DAT_VENC"], "10/11/2026")
        self.assertEqual(written_dict["AI"], "ABC1234")
        self.assertEqual(written_dict["VALOR"], "150,00")


if __name__ == "__main__":
    unittest.main()
