# Gaia — Intelligent PDF Data Extractor (CLI & Programmatic Library)

**Gaia** is a versatile and robust PDF data extraction system designed to retrieve structured key-value pair (KVP) records from PDF documents. It is packaged both as a **programmatic Python library** (`gaia`) and a feature-rich **command-line tool (CLI)**.

Gaia uses a modular architecture using fast native text extraction to ensure high speed and fidelity.

---

## 🚀 Key Features

* **Dual-Purpose Design**:
  * **Programmatic Library**: Install `gaia-pdf-parser` and integrate `OcrParser`, `RegexEngine`, and other components directly into your own codebase.
  * **Command-Line Interface**: Run parsing pipelines directly from your shell with dynamic dashboards, detailed progress tracking, and configurable execution.
* **Fast Native PDF Processing**:
  * Employs fast native layout-based text extraction (via `pypdf`).
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
├── cli/
│   ├── __init__.py          # CLI subpackage initialization
│   ├── app_controller.py    # Main orchestration of CLI execution
│   └── terminal_ui.py       # Rich TUI display and keyboard input handling
├── config/
│   ├── __init__.py
│   └── settings.py          # Global settings, arguments parsing, state persistence
├── gaia/
│   ├── __init__.py          # Main entry points exposing library API classes
│   ├── csv_writer.py        # Streamlined thread-safe CSV writing
│   ├── extraction_session.py# Session progress tracking & No-Op placeholders
│   ├── extractor.py         # Native PDF text extraction engine
│   ├── i18n.py              # Internationalization & gettext wrapper
│   ├── locale/              # Compiled translations directory
│   │   ├── en/LC_MESSAGES/messages.mo
│   │   └── pt/LC_MESSAGES/messages.mo
│   ├── observer.py          # Progress notification interface (observer pattern)
│   ├── ocr_parser.py        # Key-Value Pair regex matcher and verification
│   └── regex_engine.py      # Abstracted matching engine
├── main.py                  # CLI binary / entry point
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

You can import and use the components of Gaia directly within Python without needing the CLI or a console wrapper.

```python
from gaia import DefaultOcrParser, NativeRegexEngine, NativePdfExtractor, pos_processing_text

# 1. Setup the Regex engine with rules already in-memory (dictionary)
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
parser = DefaultOcrParser(extractor=NativePdfExtractor())

# 3. Process files programmatically
# The parser yields raw text segments for each page/unit.
# You then normalize the text and parse it using the RegexEngine.
for unit_index, total_units, raw_text in parser.process_file("path/to/infraction.pdf", pages_per_unit=1):
    record = engine.parse(raw_text)
    print("Parsed Record:", record)
```

---

### 2. Command-Line Interface (CLI)

Gaia can be executed directly as a global shell command, as a python module run, or as a local script.

```bash
# 1. As a global command (after package installation)
gaia <input_dir> [options]

# 2. As a python module run
python -m gaia <input_dir> [options]

# 3. As a local script (from the repository root)
python main.py <input_dir> [options]
```

#### Positional Arguments
* `<input_dir>`: Path to the directory containing the PDF files to process.

#### Options
* `-o`, `--output` `<path>`: Custom output CSV file path (Default: `output.csv` in your working directory).
* `-g`, `--regex` `<path>`: Path to a JSON file containing customized regex extraction rules.
* `-r`, `--recursive`: Search for PDF files recursively within subdirectories.
* `--resume`: Resume processing using checkpoint data from `.gaia_resume.json`.
* `-t`, `--test` `<file_path>`: Test your regex rules on the first page of the provided PDF.
* `-p`, `--pages-per-unit` `<int>`: The number of pages grouped together as a single block for extraction matching (Default: `1`).
* `-l`, `--lang` `{"en", "pt"}`: Force the interface language to English or Portuguese (Default: `en`).

#### Examples

* **Basic processing run**:
  ```bash
  gaia /path/to/pdfs -g rules.json
  ```

* **Resume an interrupted run**:
  ```bash
  gaia /path/to/pdfs --resume
  ```

* **Test matching logic on a single file**:
  ```bash
  gaia -t sample.pdf -g rules.json
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
