import os
import sqlite3
import pytest
from pyingestion.output_stream import SqliteOutputStream


def test_sqlite_output_stream_auto_creation_and_insertion(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    table_name = "pdf_records"

    stream = SqliteOutputStream(db_path, table_name)

    # Write first record to trigger initialization
    record_1 = {"id": "1", "name": "Alice", "role": "Developer"}
    stream.write(record_1)

    # Write second record
    record_2 = {"id": "2", "name": "Bob", "role": "Architect"}
    stream.write(record_2)

    # Verify table and data directly
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Check table columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        assert columns == ["id", "name", "role"]

        # Check rows
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY id")
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0] == ("1", "Alice", "Developer")
        assert rows[1] == ("2", "Bob", "Architect")
    finally:
        conn.close()
