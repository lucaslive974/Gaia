"""
PyIngestion (Codename: Gaia)
"""

from pyingestion.transform_stream import (
    TransformStream,
    ParallelTransformStream,
    ChainedTransformStream,
    RegexEngine,
    NativeRegexEngine,
)
from pyingestion.input_stream import (
    InputStream,
    FileInputStream,
)
from pyingestion.input_streams import (
    InputStreamFactory,
    PdfInputStream,
    DocxInputStream,
    OcrInputStream,
)
from pyingestion.extraction_session import (
    ExtractionSession,
    NoOpExtractionSession,
    FileExtractionSession,
)
from pyingestion.output_stream import (
    OutputStream,
    MultiOutputStream,
    CsvWriteStream,
    DefaultOutputStream,
    SqliteOutputStream,
    MysqlOutputStream,
)
from pyingestion.observer import (
    ExtractionObserver,
    QueueObserver,
    DefaultExtractionObserver,
)
from pyingestion.pyingestion import PyIngestion

from pyingestion.types import T_source, T_in, T_out

# Codename for reference
Gaia = PyIngestion

__all__ = [
    Gaia,
    PdfInputStream,
    DocxInputStream,
    OcrInputStream,
    TransformStream,
    ParallelTransformStream,
    ChainedTransformStream,
    RegexEngine,
    NativeRegexEngine,
    InputStream,
    FileInputStream,
    InputStreamFactory,
    ExtractionSession,
    NoOpExtractionSession,
    FileExtractionSession,
    OutputStream,
    MultiOutputStream,
    CsvWriteStream,
    DefaultOutputStream,
    SqliteOutputStream,
    MysqlOutputStream,
    ExtractionObserver,
    QueueObserver,
    DefaultExtractionObserver,
    T_in,
    T_out,
    T_source,
]
