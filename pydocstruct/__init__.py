"""
PyDocStruct (Codename: Gaia)
"""
from pydocstruct.pdf_parser import PdfParser
from pydocstruct.regex_engine import RegexEngine, NativeRegexEngine
from pydocstruct.extraction_session import ExtractionSession, NoOpExtractionSession
from pydocstruct.output_stream import OutputStream, CsvWriteStream, DefaultOutputStream
from pydocstruct.observer import ExtractionObserver, QueueObserver, DefaultExtractionObserver
from pydocstruct.pydocstruct import PyDocStruct
from pydocstruct.options import Options, options
from pydocstruct.parser import Parser, ParserType, ParserFactory

# Codename for reference
Gaia = PyDocStruct
