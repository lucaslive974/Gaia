"""
PyIngestion (Codename: Gaia)
"""
from pyingestion.parsers import PdfParser, DocxParser, OcrParser
from pyingestion.regex_engine import RegexEngine, NativeRegexEngine
from pyingestion.extraction_session import ExtractionSession, NoOpExtractionSession
from pyingestion.stream import (
    InputStream,
    TransformStream,
    OutputStream,
    MultiOutputStream,
    ParallelTransformStream,
    ChainedTransformStream,
)
from pyingestion.output_stream import CsvWriteStream, DefaultOutputStream
from pyingestion.observer import ExtractionObserver, QueueObserver, DefaultExtractionObserver
from pyingestion.pyingestion import PyIngestion
from pyingestion.options import Options, options
from pyingestion.parser import Parser, ParserType, ParserFactory

# Codename for reference
Gaia = PyIngestion
