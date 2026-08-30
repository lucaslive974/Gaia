import json
import os
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from pyingestion import PyIngestion
from pyingestion.cli.builder import (
    build_output_stream_from_config,
    build_transform_stream_from_config,
)
from pyingestion.cli.cli_helper import cli
from pyingestion.config_models import PipelineConfig
from pyingestion.input_stream import InputStream
from pyingestion.rag_streams import ChunkerTransformStream, SqliteVectorOutputStream


@pytest.fixture(autouse=True)
def mock_sentence_transformers():
    # Mock SentenceTransformer class to avoid loading the real model and downloading weights during tests
    with patch("sentence_transformers.SentenceTransformer") as mock_class:
        mock_instance = mock_class.return_value
        # Mock encode to return a dummy embedding of 384 dimensions
        mock_instance.encode.return_value = [0.1] * 384
        yield mock_class


def test_chunker_transform_stream_logic() -> None:
    # Test text chunker with default embedder (which is mocked to return [0.1]*384)
    text = "abcdefghij"  # 10 chars
    # chunk_size = 4, chunk_overlap = 2
    # expected chunks:
    # 0: 'abcd'
    # 1: 'cdef'
    # 2: 'efgh'
    # 3: 'ghij'
    stream = ChunkerTransformStream(chunk_size=4, chunk_overlap=2)
    res = stream.transform(text)

    assert len(res) == 4
    assert res[0]["text"] == "abcd"
    assert res[1]["text"] == "cdef"
    assert res[2]["text"] == "efgh"
    assert res[3]["text"] == "ghij"
    assert all(len(cast(list[float], item["embedding"])) == 384 for item in res)
    assert all(cast(list[float], item["embedding"])[0] == 0.1 for item in res)
    assert res[0]["chunk_index"] == 0
    assert cast(dict[str, int], res[0]["metadata"])["length"] == 4


def test_chunker_transform_stream_custom_embedder() -> None:
    def custom_embedder(text: str) -> list[float]:
        return [float(len(text)), 2.0]

    stream = ChunkerTransformStream(
        chunk_size=5, chunk_overlap=1, embedder=custom_embedder
    )
    res = stream.transform("abc")
    assert len(res) == 1
    assert res[0]["text"] == "abc"
    assert res[0]["embedding"] == [3.0, 2.0]


def test_sqlite_vector_output_stream(tmp_path: Path) -> None:
    db_path = os.path.join(tmp_path, "vector_test.db")
    table_name = "test_embeddings"

    stream = SqliteVectorOutputStream(db_path=db_path, table_name=table_name)

    # Write some dummy chunks
    chunks: list[dict[str, object]] = [
        {"text": "hello", "embedding": [0.1, 0.2], "metadata": {"source": "doc1"}},
        {"text": "world", "embedding": [0.3, 0.4], "metadata": {"source": "doc2"}},
    ]

    stream.write(chunks)

    # Verify DB directly
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT text, embedding, metadata FROM {table_name}")
        rows = cast(list[tuple[str, str, str]], cursor.fetchall())
        assert len(rows) == 2
        assert rows[0][0] == "hello"
        assert json.loads(rows[0][1]) == [0.1, 0.2]
        assert json.loads(rows[0][2]) == {"source": "doc1"}

        assert rows[1][0] == "world"
        assert json.loads(rows[1][1]) == [0.3, 0.4]
        assert json.loads(rows[1][2]) == {"source": "doc2"}
    finally:
        conn.close()


def test_rag_pipeline_builder_integration() -> None:
    # Test configuring RAG pipeline from a dict/pydantic config
    config_dict = {
        "transform": {"type": "embed", "chunk_size": 250, "chunk_overlap": 50},
        "output": {
            "type": "sqlite-vector",
            "db_path": "rag_test.db",
            "table_name": "custom_chunks",
        },
    }

    p_config = PipelineConfig.model_validate(config_dict)

    transform_stream = build_transform_stream_from_config(p_config)
    assert isinstance(transform_stream, ChunkerTransformStream)
    assert transform_stream.chunk_size == 250
    assert transform_stream.chunk_overlap == 50

    output_stream = build_output_stream_from_config(p_config)
    assert isinstance(output_stream, SqliteVectorOutputStream)
    assert output_stream.db_path == "rag_test.db"
    assert output_stream.table_name == "custom_chunks"


def test_transform_stream_factory() -> None:
    from pyingestion.transform_stream import TransformStreamFactory, TransformStreamType

    # Test factory creation of embed stream
    stream = TransformStreamFactory.create(
        TransformStreamType.EMBED,
        {"chunk_size": 300, "chunk_overlap": 40, "device": "cpu"},
    )
    assert isinstance(stream, ChunkerTransformStream)
    assert stream.chunk_size == 300
    assert stream.chunk_overlap == 40
    assert stream.device == "cpu"

    # Test factory creation of regex stream with missing file (should raise ValueError)
    with pytest.raises(ValueError) as exc_info:
        TransformStreamFactory.create("regex", {})
    assert "Transform of type 'regex' requires" in str(exc_info.value)

    # Test unknown type
    with pytest.raises(ValueError) as exc_info:
        TransformStreamFactory.create("unknown_type")
    assert "Unknown transform type" in str(exc_info.value)


def test_rag_pipeline_builder_default_and_string_config() -> None:
    # Test build_output_stream_from_config string shortcuts
    # 1. string shortcut
    p_config_str = PipelineConfig.model_validate(
        {"to": "sqlite-vector", "output": "vector_direct.db"}
    )
    output_stream_str = build_output_stream_from_config(p_config_str)
    assert isinstance(output_stream_str, SqliteVectorOutputStream)
    assert output_stream_str.db_path == "vector_direct.db"

    # 2. no output dict: uses default to_dest
    p_config_default = PipelineConfig.model_validate({"to": "sqlite-vector"})
    output_stream_default = build_output_stream_from_config(p_config_default)
    assert isinstance(output_stream_default, SqliteVectorOutputStream)
    assert output_stream_default.db_path == "vector_store.db"


def test_cli_rag_integration(
    temp_file_factory: Callable[[str, str | dict[str, object], bool], str],
) -> None:
    toml_content = """
    input_dir = "/dummy/rag/input"

    [input]
    type = "pdf"
    pages_per_unit = 1

    [transform]
    type = "embed-transform"
    chunk_size = 300
    chunk_overlap = 60

    [output]
    type = "sqlite-vector"
    db_path = "rag_cli.db"
    table_name = "cli_chunks"
    """
    config_file = temp_file_factory("pipeline_rag.toml", toml_content, False)

    runner = CliRunner()
    with patch("pyingestion.cli.terminal_ui.run_with_ui") as mock_run:
        result = runner.invoke(cli, ["--config", config_file])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args  # pyright: ignore[reportAny]
        assert args[0] == "/dummy/rag/input"
        assert isinstance(kwargs["input_stream"], InputStream)

        transform_stream = kwargs["transform_stream"]  # pyright: ignore[reportAny]
        assert isinstance(transform_stream, ChunkerTransformStream)
        assert transform_stream.chunk_size == 300
        assert transform_stream.chunk_overlap == 60

        output_stream = kwargs["output_stream"]  # pyright: ignore[reportAny]
        assert isinstance(output_stream, SqliteVectorOutputStream)
        assert output_stream.db_path == "rag_cli.db"
        assert output_stream.table_name == "cli_chunks"


def test_full_rag_pipeline_execution(tmp_path: Path) -> None:
    # Test orchestrator running with chunker and sqlite-vector
    db_path = os.path.join(tmp_path, "pipeline_execution.db")

    from collections.abc import Generator

    from pyingestion.extraction_session import ExtractionSession

    # Mocking input stream that yields paragraphs
    class DummyInputStream(InputStream[str, str]):
        def __init__(self) -> None:
            super().__init__()

        def read(
            self, source: str, session: ExtractionSession | None = None
        ) -> Generator[str, None, None]:
            yield "This is a first block of text that should be chunked."
            yield "This is a second block of text for processing."

    input_stream = DummyInputStream()
    transform_stream = ChunkerTransformStream(chunk_size=10, chunk_overlap=2)
    output_stream = SqliteVectorOutputStream(
        db_path=db_path, table_name="pipeline_embeddings"
    )

    controller = PyIngestion()
    success = controller.process(
        source=str(tmp_path),
        input_stream=input_stream,
        transform_stream=transform_stream,
        output_stream=output_stream,
    )

    assert success is True

    # Verify SQLite DB
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT text, embedding, metadata FROM pipeline_embeddings")
        rows = cast(list[tuple[str, str, str]], cursor.fetchall())
        assert len(rows) > 0
        # Check that one of the texts contains chunked pieces
        assert all(len(row[0]) <= 10 for row in rows)
        # Embedding is serialized JSON
        embedding = cast(list[float], json.loads(rows[0][1]))
        assert len(embedding) == 384
    finally:
        conn.close()


def test_chunker_transform_stream_production_path_missing_dependency() -> None:
    with patch.dict("sys.modules", {"sentence_transformers": None}):
        with pytest.raises(ImportError) as exc_info:
            ChunkerTransformStream(chunk_size=4, chunk_overlap=2)
        assert "The 'sentence-transformers' package is required" in str(exc_info.value)


def test_cli_embed_transform_command() -> None:
    runner = CliRunner()
    with patch("pyingestion.cli.terminal_ui.run_with_ui") as mock_run:
        result = runner.invoke(
            cli,
            [
                "--source",
                "/dummy",
                "pdf-input",
                "embed-transform",
                "--chunk-size",
                "350",
                "--chunk-overlap",
                "75",
                "--device",
                "cpu",
                "sqlite-vector-output",
                "--db",
                "test_cli_db.db",
                "--table",
                "cli_table",
            ],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args  # pyright: ignore[reportAny]
        assert args[0] == "/dummy"

        transform_stream = kwargs["transform_stream"]  # pyright: ignore[reportAny]
        assert isinstance(transform_stream, ChunkerTransformStream)
        assert transform_stream.chunk_size == 350
        assert transform_stream.chunk_overlap == 75
        assert transform_stream.device == "cpu"

        output_stream = kwargs["output_stream"]  # pyright: ignore[reportAny]
        assert isinstance(output_stream, SqliteVectorOutputStream)
        assert output_stream.db_path == "test_cli_db.db"
        assert output_stream.table_name == "cli_table"
