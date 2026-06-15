"""
PyIngestion (Codename: Gaia)
"""
from pyingestion.parsers import PdfParser, DocxParser, OcrParser
from pyingestion.transform_stream import (
    TransformStream,
    ParallelTransformStream,
    ChainedTransformStream,
    RegexEngine,
    NativeRegexEngine,
)
from pyingestion.input_stream import (
    InputStream,
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
from pyingestion.options import Options, options

# Codename for reference
Gaia = PyIngestion
