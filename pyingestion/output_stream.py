import csv
from os import path
from enum import Enum
from collections.abc import Mapping
from typing import Generic, cast 
from pyingestion.types import T_out


class OutputStream(Generic[T_out]):
    input_type: type[T_out] = cast(type[T_out], object)

    def write(self, item: T_out) -> None:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError


class MultiOutputStream(OutputStream[T_out]):
    input_type: type[T_out] = cast(type[T_out], object)

    def __init__(self, streams: list[OutputStream[T_out]]):
        self.streams = streams
        if streams:
            self.input_type = streams[0].input_type

    def write(self, item: T_out) -> None:
        for stream in self.streams:
            stream.write(item)


class CsvWriteStream(OutputStream[dict[str, str]]):
    def __init__(self, path_output: str = "output.csv"):
        self._path = path_output

    def get_path(self):
        return self._path

    def write(self, item: dict[str, str]):
        output_path = self._path
        file_exists = path.exists(output_path)

        with open(output_path, mode="a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file, fieldnames=item.keys(), skipinitialspace=True
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(item)


class DefaultOutputStream(OutputStream[dict[str, str]]):
    def __init__(self):
        self._data = []

    def write(self, item: dict[str, str]):
        self._data.append(item)

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

        import sqlite3

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            sanitized_table = "".join(
                c for c in self.table_name if c.isalnum() or c == "_"
            )
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
                values,
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
            import pymysql  # pyright: ignore[reportMissingModuleSource]
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

        import pymysql  # pyright: ignore[reportMissingModuleSource]

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


class OutputStreamType(Enum):
    CSV = "csv"
    SQLITE = "sqlite"
    MYSQL = "mysql"


class OutputStreamFactory:
    @staticmethod
    def create(
        output_type: str | OutputStreamType,
        config: Mapping[str, object] | None = None,
    ) -> OutputStream[dict[str, str]]:
        import os
        from pyingestion.output_stream import (
            CsvWriteStream,
            SqliteOutputStream,
            MysqlOutputStream,
        )

        pt = (
            output_type.value
            if isinstance(output_type, OutputStreamType)
            else output_type.lower()
        )

        cfg = config or {}

        if pt == "csv":
            out_path = str(cfg.get("path") or cfg.get("output") or "output.csv")
            return CsvWriteStream(out_path)
        elif pt == "sqlite":
            db_path = str(cfg.get("db_path") or cfg.get("path") or "records.db")
            table_name = str(cfg.get("table_name") or cfg.get("table") or "extracted_data")
            return SqliteOutputStream(db_path, table_name)
        elif pt == "mysql":
            conn_uri = str(
                cfg.get("connection_uri")
                or cfg.get("connection")
                or os.environ.get("DATABASE_URL")
                or ""
            )
            if not conn_uri:
                raise ValueError(
                    "MySQL output requires 'connection_uri' or env var 'DATABASE_URL'."
                )
            table_name = str(cfg.get("table_name") or cfg.get("table") or "extracted_data")
            return MysqlOutputStream(connection_uri=conn_uri, table_name=table_name)
        else:
            raise ValueError(f"Unknown output type: {pt}")
