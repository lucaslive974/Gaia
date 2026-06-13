"""
PyDocStructurer (Codename: Gaia)
"""
from pydocstructurer.parsers import PdfParser, DocxParser
from pydocstructurer.regex_engine import RegexEngine, NativeRegexEngine
from pydocstructurer.extraction_session import ExtractionSession, NoOpExtractionSession
from pydocstructurer.output_stream import OutputStream, CsvWriteStream, DefaultOutputStream
from pydocstructurer.observer import ExtractionObserver, QueueObserver, DefaultExtractionObserver
from pydocstructurer.pydocstructurer import PyDocStructurer
from pydocstructurer.options import Options, options
from pydocstructurer.parser import Parser, ParserType, ParserFactory

# Codename for reference
Gaia = PyDocStructurer
