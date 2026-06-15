import csv
from os import path
from typing import Any, Generic, TypeVar
from pyingestion.options import options

T_in = TypeVar("T_in")


class OutputStream(Generic[T_in]):
    input_type: type[T_in] = Any

    def write(self, item: T_in) -> None:
        raise NotImplementedError


class MultiOutputStream(OutputStream[T_in]):
    input_type: type[T_in] = Any

    def __init__(self, streams: list[OutputStream[T_in]]):
        self.streams = streams
        if streams:
            self.input_type = streams[0].input_type

    def write(self, item: T_in) -> None:
        for stream in self.streams:
            stream.write(item)


class CsvWriteStream(OutputStream[dict[str, str]]):
    def __init__(self, path_output: str | None = None):
        self._path = path_output

    def write(self, content: dict[str, str]):
        output_path = self._path or options["OUTPUT_CSV"]
        file_exists = path.exists(output_path)

        with open(output_path, mode="a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file, fieldnames=content.keys(), skipinitialspace=True
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(content)


class DefaultOutputStream(OutputStream[dict[str, str]]):
    def __init__(self):
        self._data = []

    def write(self, content: dict[str, str]):
        self._data.append(content)

    def __iter__(self):
        for item in self._data:
            yield item


class SqliteOutputStream(OutputStream[dict[str, str]]):
    def __init__(self, db_path: str, table_name: str = "extracted_data"):
        self.db_path = db_path
        self.table_name = table_name
        self._initialized = False

    def _initialize(self, sample_dict: dict[str, str]):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            sanitized_table = "".join(c for c in self.table_name if c.isalnum() or c == "_")
            columns = []
            for key in sample_dict.keys():
                sanitized_col = "".join(c for c in key if c.isalnum() or c == "_")
                columns.append(f"{sanitized_col} TEXT")
            
            columns_str = ", ".join(columns)
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {sanitized_table} ({columns_str})")
            conn.commit()
        finally:
            conn.close()
        self._initialized = True

    def write(self, item: dict[str, str]) -> None:
        if not item:
            return
        if not self._initialized:
            self._initialize(item)
        
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            sanitized_table = "".join(c for c in self.table_name if c.isalnum() or c == "_")
            keys = []
            values = []
            for k, v in item.items():
                sanitized_key = "".join(c for c in k if c.isalnum() or c == "_")
                keys.append(sanitized_key)
                values.append(v)
            
            placeholders = ", ".join(["?"] * len(keys))
            columns_str = ", ".join(keys)
            cursor.execute(
                f"INSERT INTO {sanitized_table} ({columns_str}) VALUES ({placeholders})",
                values
            )
            conn.commit()
        finally:
            conn.close()


class MysqlOutputStream(OutputStream[dict[str, str]]):
    def __init__(
        self,
        host: str = "localhost",
        user: str = "root",
        password: str = "",
        database: str = "",
        port: int = 3306,
        table_name: str = "extracted_data",
        connection_uri: str | None = None,
    ):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.database = database
        self.table_name = table_name
        self.connection_uri = connection_uri
        self._initialized = False

        if connection_uri:
            import re
            m = re.match(
                r"mysql(?:\+pymysql)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)",
                connection_uri,
            )
            if m:
                self.user = m.group(1)
                self.password = m.group(2)
                self.host = m.group(3)
                port_str = m.group(4)
                self.port = int(port_str) if port_str else 3306
                self.database = m.group(5)

    def _initialize(self, sample_dict: dict[str, str]):
        try:
            import pymysql
        except ImportError:
            raise ImportError(
                "The 'pymysql' package is required for MySQL output. Please install it using 'pip install pymysql'."
            )

        conn = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=self.database,
        )
        try:
            with conn.cursor() as cursor:
                sanitized_table = "".join(
                    c for c in self.table_name if c.isalnum() or c == "_"
                )
                columns = []
                for key in sample_dict.keys():
                    sanitized_col = "".join(c for c in key if c.isalnum() or c == "_")
                    columns.append(f"{sanitized_col} TEXT")

                columns_str = ", ".join(columns)
                cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS {sanitized_table} ({columns_str})"
                )
                conn.commit()
        finally:
            conn.close()
        self._initialized = True

    def write(self, item: dict[str, str]) -> None:
        if not item:
            return
        if not self._initialized:
            self._initialize(item)

        import pymysql
        conn = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=self.database,
        )
        try:
            with conn.cursor() as cursor:
                sanitized_table = "".join(
                    c for c in self.table_name if c.isalnum() or c == "_"
                )
                keys = []
                values = []
                for k, v in item.items():
                    sanitized_key = "".join(c for c in k if c.isalnum() or c == "_")
                    keys.append(sanitized_key)
                    values.append(v)

                placeholders = ", ".join(["%s"] * len(keys))
                columns_str = ", ".join(keys)
                cursor.execute(
                    f"INSERT INTO {sanitized_table} ({columns_str}) VALUES ({placeholders})",
                    values,
                )
                conn.commit()
        finally:
            conn.close()
