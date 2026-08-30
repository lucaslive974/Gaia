import json
import sqlite3
from collections.abc import Callable, Mapping
from typing import Any

from pyingestion.i18n import _
from pyingestion.output_stream import OutputStream
from pyingestion.transform_stream import TransformStream, TransformStreamFactory


class ChunkerTransformStream(TransformStream[str, list[dict[str, object]]]):
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        embedder: Callable[[str], list[float]] | None = None,
        device: str | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.device = device
        if embedder is not None:
            self.embedder = embedder
        else:
            try:
                from sentence_transformers import SentenceTransformer

                self._model: SentenceTransformer | None = None

                def sentence_transformer_embedder(text: str) -> list[float]:
                    if self._model is None:
                        self._model = SentenceTransformer(
                            "all-MiniLM-L6-v2", device=self.device
                        )
                    emb = self._model.encode(text)
                    if hasattr(emb, "tolist"):
                        return [float(x) for x in emb.tolist()]
                    return [float(x) for x in emb]

                self.embedder = sentence_transformer_embedder
            except ImportError as e:
                raise ImportError(_("err_sentence_transformers_required")) from e

    def transform(self, data: str) -> list[dict[str, object]]:
        chunks = self._chunk_text(data)
        results = []
        for i, chunk in enumerate(chunks):
            embedding = self.embedder(chunk)
            results.append(
                {
                    "chunk_index": i,
                    "text": chunk,
                    "embedding": embedding,
                    "metadata": {
                        "length": len(chunk),
                    },
                }
            )
        return results

    def _chunk_text(self, text: str) -> list[str]:
        if not text:
            return []
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
            if start >= text_len or (end >= text_len):
                break
        return chunks


class SqliteVectorOutputStream(OutputStream[list[dict[str, object]]]):
    def __init__(
        self, db_path: str = "vector_store.db", table_name: str = "embeddings"
    ):
        self.db_path = db_path
        self.table_name = table_name
        self._initialized = False

    def _initialize(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()
        self._initialized = True

    def write(self, item: list[dict[str, object]]) -> None:
        if not self._initialized:
            self._initialize()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            for chunk_data in item:
                text = chunk_data["text"]
                embedding_str = json.dumps(chunk_data["embedding"])
                metadata_str = json.dumps(chunk_data.get("metadata", {}))

                cursor.execute(
                    f"INSERT INTO {self.table_name} (text, embedding, metadata) VALUES (?, ?, ?)",
                    (text, embedding_str, metadata_str),
                )
            conn.commit()
        finally:
            conn.close()


def _create_chunker(cfg: Mapping[str, object]) -> TransformStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
    val_size = cfg.get("chunk_size")
    chunk_size = int(val_size) if isinstance(val_size, (int, str)) else 500
    val_overlap = cfg.get("chunk_overlap")
    chunk_overlap = int(val_overlap) if isinstance(val_overlap, (int, str)) else 100
    device = cfg.get("device")
    device_str = str(device) if device is not None else None
    return ChunkerTransformStream(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        device=device_str,
    )


TransformStreamFactory.register("embed", _create_chunker)
TransformStreamFactory.register("embed-transform", _create_chunker)
