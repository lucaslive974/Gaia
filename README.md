# PyDocStruct (Codename: Gaia) — Generalized Document Data Extractor

**PyDocStruct** (project codename **Gaia**) is a versatile and robust document data extraction system designed to retrieve structured key-value pair (KVP) records from text and files. It is packaged both as a **programmatic Python library** (`pydocstruct`) and a feature-rich **command-line tool (CLI)**.

PyDocStruct uses a modular architecture using fast native text extraction and an extensible parser interface to ensure high speed, fidelity, and future adaptability to new file formats.

---

## 🚀 Key Features

* **Dual-Purpose Design**:
  * **Programmatic Library**: Integrate the `RegexEngine`, built-in or custom `Parser` components, and observers directly into your own codebase.
  * **Command-Line Interface**: Run parsing pipelines directly from your shell with dynamic dashboards, detailed progress tracking, and configurable execution.
* **Extensible Parser Architecture**:
  * Fully decoupled document discovery and data extraction. Programmatic users can write and inject custom parsers (e.g., Docx, OCR, XML) by subclassing the abstract `Parser` class.
* **Fast Native PDF Processing**:
  * Employs fast native layout-based PDF text extraction (via `pypdf`) as a built-in default parser.
* **Dynamic Terminal Interface (TUI)**:
  * Real-time metrics rendered via `rich.live`.
  * Live status dashboard featuring counters for processed files, pages, failures, and a progress bar with numerical Estimated Time of Arrival (**ETA**).
* **Robust Session Resume**:
  * Automatically checkpoints progress using a state file (`.gaia_resume.json`). If interrupted, the `--resume` flag lets you pick up right where you left off.
* **Custom Regex Configurations**:
  * Supply custom pattern matching rules via a JSON configuration file.
* **Multi-Page Unit Grouping**:
  * Group multiple pages as a single unit using `--pages-per-unit` for patterns that span across page boundaries.
* **Internationalization (i18n)**:
  * Complete user interface and message translation support for English (`en`) and Portuguese (`pt`).
* **Graceful Interrupt Handlers**:
  * Supports clean cancellation via `ESC` or `Ctrl+C`, ensuring resources, files, and terminal settings are restored safely.

---

## 📁 Project Directory Structure

```text
Gaia/
├── pydocstruct/
│   ├── __init__.py          # Main entry points exposing library API classes
│   ├── __main__.py          # Main entry point for python -m pydocstruct
│   ├── cli/
│   │   ├── __init__.py      # CLI subpackage initialization
│   │   ├── cli_helper.py    # CLI arguments parser and prevalidation helper
│   │   └── terminal_ui.py   # Rich TUI display and keyboard input handling
│   ├── pydocstruct.py       # Main global program class (PyDocStruct, codename: Gaia)
│   ├── extraction_session.py# Session progress tracking & state serialization
│   ├── options.py           # Config options container class & parameter validations
│   ├── parser.py            # Abstract Parser base, ParserType Enum, and ParserFactory
│   ├── i18n.py              # Gettext wrappers and language initialization
│   ├── locale/              # Compiled translations directory
│   │   ├── en/LC_MESSAGES/messages.mo
│   │   └── pt/LC_MESSAGES/messages.mo
│   ├── observer.py          # Progress notification interface (observer pattern)
│   ├── output_stream.py     # Output stream interfaces (OutputStream, CsvWriteStream, DefaultOutputStream)
│   ├── pdf_parser.py        # Native PDF Parser implementation
│   ├── regex_engine.py      # Abstracted matching engine
│   └── main.py              # CLI entry point implementation
├── pyproject.toml           # Setuptools PEP 621 packaging definitions
├── requirements.txt         # Package requirements
├── tests/                   # Extensive test suites
└── tools/
    └── linux/
        ├── compile_locales.sh # Compiles Translation Catalog (.po -> .mo)
        └── run_tests.sh       # Script to execute unittest suite
```

---

## 🛠️ Requirements & Installation

### Prerequisites
1. **Python 3.10+**

### Environment Setup & Packaging

1. Clone or navigate to the repository:
   ```bash
   cd Trabalho/Gaia
   ```

2. Setup virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

---

## 💻 Usage

### 1. As a Python Library

You can integrate PyDocStruct directly into your Python scripts.

#### Orchestrating the Full Pipeline Programmatically

To execute the entire extraction pipeline on a file or directory:

```python
from pydocstruct import PyDocStruct, Options

# 1. Configure options programmatically
options = Options()
options.BASE_PATH = "path/to/pdfs"
options.REGEX_FILE = "path/to/rules.json"
options.OUTPUT_CSV = "custom_output.csv"
options.PAGES_PER_UNIT = 1

# 2. Run the orchestrator
controller = PyDocStruct(options)
success = controller.run()
```

#### Creating & Injecting a Custom Parser

You can supply your own extraction parser format by subclassing the abstract base class `Parser`:

```python
from typing import Generator
from pydocstruct import PyDocStruct, Options, Parser, ExtractionSession

class CustomTxtParser(Parser):
    def accepts(self, file_path: str) -> bool:
        # Define what files this parser accepts
        return file_path.lower().endswith(".txt")

    def process_file(
        self,
        file_path: str,
        session: ExtractionSession | None = None,
        pages_per_unit: int = 1
    ) -> Generator[tuple[int, int, str], None, None]:
        # Process the file and yield: (unit_index, total_units, content_text)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        yield 1, 1, content

# Inject it into PyDocStruct orchestrator
options = Options()
options.BASE_PATH = "path/to/text/files"
options.REGEX_FILE = "rules.json"

controller = PyDocStruct(options, parser=CustomTxtParser())
controller.run()
```

#### Using Parser and Engine Components Directly

To parse files manually and match patterns page-by-page:

```python
from pydocstruct import PdfParser, NativeRegexEngine

# 1. Setup the Regex engine with rules in-memory (dictionary)
regex_rules = {
    "infraction_id": {
        "regex": r"Código da Infração:\s*([A-Za-z0-9-]+)",
        "required": True
    },
    "plate": {
        "regex": r"Placa:\s*([A-Z]{3}-?\d[A-Z0-9]\d{2})",
        "required": True
    }
}
engine = NativeRegexEngine(regex_rules)

# Alternatively, load rules from a JSON file path:
# engine = NativeRegexEngine.from_file("path/to/rules.json")

# 2. Setup the parser
parser = PdfParser()

# 3. Process files programmatically
# The parser yields raw text segments for each page/unit.
# You then normalize the text and parse it using the RegexEngine.
for unit_index, total_units, raw_text in parser.process_file("path/to/infraction.pdf", pages_per_unit=1):
    record = engine.parse(raw_text)
    print("Parsed Record:", record)
```

---

### 2. Command-Line Interface (CLI)

PyDocStruct can be executed directly as a global shell command, as a python module run, or as a local script.

```bash
# 1. As a global command (after package installation)
pydocstruct <input_dir> [options]

# 2. As a python module run (from the repository root)
python -m pydocstruct <input_dir> [options]
```

#### Positional Arguments
* `<input_dir>`: Path to the directory containing files to process.

#### Options
* `-o`, `--output` `<path>`: Custom output CSV file path (Default: `output.csv` in your working directory).
* `-g`, `--regex` `<path>`: Path to a JSON file containing customized regex extraction rules.
* `-r`, `--recursive`: Search for files recursively within subdirectories.
* `--resume`: Resume processing using checkpoint data from `.gaia_resume.json`.
* `-t`, `--test` `<file_path>`: Test your regex rules on the first page of the provided file.
* `-p`, `--pages-per-unit` `<int>`: The number of pages/chunks grouped together as a single block for extraction matching (Default: `1`).
* `-l`, `--lang` `{"en", "pt"}`: Force the interface language to English or Portuguese (Default: `en`).
* `--type` `{"pdf"}`: Define the built-in parser type to use (Default: `pdf`).

#### Examples

* **Basic processing run**:
  ```bash
  pydocstruct /path/to/pdfs -g rules.json
  ```

* **Resume an interrupted run**:
  ```bash
  pydocstruct /path/to/pdfs --resume
  ```

* **Test matching logic on a single file**:
  ```bash
  pydocstruct -t sample.pdf -g rules.json
  ```

---

## 🧪 Testing and Tools

### Running the Test Suite
The unit and integration tests validate CLI logic, parser fallbacks, observers, and settings parsing.
```bash
./tools/linux/run_tests.sh
```

### Compiling Localization Catalogs
To re-compile updated translation dictionary catalogs (`.po`) to gettext binary files (`.mo`):
```bash
./tools/linux/compile_locales.sh
```
