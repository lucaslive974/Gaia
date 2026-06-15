"""
PyIngestion (Codename: Gaia)
"""
from pyingestion.input_streams import (
    PdfInputStream,
    DocxInputStream,
    OcrInputStream,
    PdfParser,
    DocxParser,
    OcrParser,
)
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
    InputStreamType,
    InputStreamFactory,
)
from pyingestion.extraction_session import ExtractionSession, NoOpExtractionSession
from pyingestion.output_stream import (
    OutputStream,
    MultiOutputStream,
    CsvWriteStream,
    DefaultOutputStream,
    SqliteOutputStream,
    MysqlOutputStream,
)
from pyingestion.observer import ExtractionObserver, QueueObserver, DefaultExtractionObserver
from pyingestion.pyingestion import PyIngestion

# Codename for reference
Gaia = PyIngestion
