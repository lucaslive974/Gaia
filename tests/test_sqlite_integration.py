import os
import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from pyingestion import PyIngestion, Options, NativeRegexEngine, SqliteOutputStream


@patch("pyingestion.pyingestion.os.listdir")
@patch("pyingestion.pyingestion.os.path.exists")
@patch("pyingestion.pyingestion.os.path.isdir")
@patch("pyingestion.parsers.PdfReader")
def test_sqlite_integration_flow(
    mock_pdf_reader, mock_isdir, mock_exists, mock_listdir, tmp_path, temp_file_factory
):
    # Mocking filesystem
    mock_isdir.return_value = True
    mock_listdir.return_value = ["invoice.pdf"]
    mock_exists.side_effect = lambda p: True

    # Mocking PDF content
    mock_reader_instance = MagicMock()
    page1 = MagicMock()
    page1.extract_text.return_value = "Title: Invoice-101"
    page2 = MagicMock()
    page2.extract_text.return_value = "Title: Invoice-102"
    mock_reader_instance.pages = [page1, page2]
    mock_pdf_reader.return_value = mock_reader_instance

    # Options
    options = Options()
    options.BASE_PATH = "/dummy/files"
    options.PARSER_TYPE = "pdf"
    options.PAGES_PER_UNIT = 1
    options.TO = "sqlite"

    db_path = os.path.join(tmp_path, "invoices.db")
    table_name = "invoices_table"
    options.OUTPUT_CSV = db_path

    # Rules file
    rules_data = {
        "invoice_title": {
            "regex": r"Title:\s*([A-Za-z0-9-]+)",
            "required": True,
            "default": ""
        }
    }
    rules_file = temp_file_factory("rules.json", rules_data, is_json=True)
    regex_engine = NativeRegexEngine.from_file(rules_file)

    # Output Stream
    output_stream = SqliteOutputStream(db_path, table_name)

    # Orchestrator
    controller = PyIngestion(options, transform_stream=regex_engine, output_stream=output_stream)

    # Run pipeline
    success = controller.run()
    assert success is True

    # Verify SQLite database contains the records
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT invoice_title FROM {table_name}")
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "Invoice-101"
        assert rows[1][0] == "Invoice-102"
    finally:
        conn.close()
