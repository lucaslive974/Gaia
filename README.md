# PyIngestion (Codename: Gaia) — Generalized Document Data Extractor

**PyIngestion** (project codename **Gaia**) is a versatile and robust document data extraction system designed to retrieve structured key-value pair (KVP) records from text and files. It is packaged both as a **programmatic Python library** (`pyingestion`) and a feature-rich **command-line tool (CLI)**.

PyIngestion uses a modular architecture using fast native text extraction and an extensible parser interface to ensure high speed, fidelity, and future adaptability to new file formats.

---

## 🚀 Key Features

* **Dual-Purpose Design**:
  * **Programmatic Library**: Integrate the `TransformStream`, built-in or custom `InputStream` components, and observers directly into your own codebase.
  * **Command-Line Interface**: Run parsing pipelines directly from your shell with dynamic dashboards, detailed progress tracking, and configurable execution.
* **Extensible Input Stream (Parser) Architecture**:
  * Fully decoupled document discovery and data extraction. Programmatic users can write and inject custom input streams (e.g., Docx, OCR, XML) by subclassing the abstract `InputStream` class.
* **Fast Native PDF Processing**:
  * Employs fast native layout-based PDF text extraction (via `pypdf`) as a built-in default input stream.
* **Dynamic Terminal Interface (TUI)**:
  * Real-time metrics rendered via `rich.live`.
  * Live status dashboard featuring counters for processed files, pages, failures, and a progress bar with numerical Estimated Time of Arrival (**ETA**).
* **Robust Session Resume**:
  * Automatically checkpoints progress using a state file (`.gaia_resume.json`) in the current directory. If interrupted, running the CLI with the `--resume` flag lets you pick up right where you left off, automatically restoring the input source, configuration, and processed files list from the checkpoint without needing to specify options again.
* **Custom Regex Configurations**:
  * Supply custom pattern matching rules via a JSON/TOML configuration file.
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
├── pyingestion/
│   ├── __init__.py          # Main entry points exposing library API classes
│   ├── __main__.py          # Main entry point for python -m pyingestion
│   ├── cli/
│   │   ├── __init__.py      # CLI subpackage initialization
│   │   ├── builder.py       # Config loaders and pipeline builders
│   │   ├── cli_helper.py    # Click group, options, commands, and callback definitions
│   │   ├── main.py          # CLI entry point implementation
│   │   └── terminal_ui.py   # Rich TUI display and keyboard input handling
│   ├── pyingestion.py       # Main stateless pipeline execution runner
│   ├── extraction_session.py# Session progress tracking & state serialization
│   ├── input_stream.py      # Abstract InputStream base and FileInputStream base
│   ├── input_streams.py     # Concrete InputStream implementations and InputStreamFactory
│   ├── i18n.py              # Gettext wrappers and language initialization
│   ├── locale/              # Compiled translations directory
│   │   ├── en/LC_MESSAGES/messages.mo
│   │   └── pt/LC_MESSAGES/messages.mo
│   ├── observer.py          # Progress notification interface (observer pattern)
│   ├── output_stream.py     # Output stream interfaces (OutputStream, CsvWriteStream, DefaultOutputStream, SqliteOutputStream, MysqlOutputStream, OutputStreamFactory)
│   ├── transform_stream.py  # Abstract and concrete TransformStream and RegexEngine implementations
│   └── types.py             # Type variable declarations for strict typing
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
1. **Python 3.11+**

### Environment Setup & Packaging

1. Clone or navigate to the repository:
   ```bash
   cd Trabajo/Gaia
   ```

2. Setup virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the package in editable mode:
   - **Standard installation** (core document parsing, regex engine):
     ```bash
     pip install -e .
     ```
   - **RAG & Embeddings installation** (includes `sentence-transformers` for generating vector embeddings):
     ```bash
     pip install -e .[rag]
     ```

---

## 💻 Usage

### 1. As a Python Library

You can integrate PyIngestion directly into your Python scripts.

#### Orchestrating the Full Pipeline Programmatically

To execute the entire extraction pipeline on a file or directory:

```python
from pyingestion import PyIngestion, PdfInputStream, NativeRegexEngine, CsvWriteStream

# 1. Load components
input_stream = PdfInputStream(pages_per_unit=1)
transform = NativeRegexEngine.from_file("path/to/rules.json")
output = CsvWriteStream("custom_output.csv")

# 2. Run the orchestrator
runner = PyIngestion()
success = runner.process(
    source="path/to/pdfs",
    input_stream=input_stream,
    transform_stream=transform,
    output_stream=output,
)
```

#### Orchestrating a RAG Ingestion Pipeline Programmatically

To perform chunking, vector embedding generation, and SQLite database persistence (RAG flow):

```python
from pyingestion import (
    PyIngestion,
    PdfInputStream,
    ChunkerTransformStream,
    SqliteVectorOutputStream,
)

# 1. Load components
input_stream = PdfInputStream(pages_per_unit=1)

# ChunkerTransformStream splits document text using chunk_size and chunk_overlap,
# and generates embeddings using the sentence-transformers library.
transform = ChunkerTransformStream(chunk_size=300, chunk_overlap=50, device="cpu")

# SqliteVectorOutputStream serializes and stores the text chunks, metadata, and embedding vectors in a SQLite DB
output = SqliteVectorOutputStream(
    db_path="rag_vector_store.db", table_name="embeddings"
)

# 2. Run the pipeline
runner = PyIngestion()
success = runner.process(
    source="path/to/pdfs",
    input_stream=input_stream,
    transform_stream=transform,
    output_stream=output,
)
```

#### Creating & Injecting a Custom Input Stream

You can supply your own extraction parser format by subclassing the abstract base class `InputStream`:

```python
from collections.abc import Generator
from pyingestion import (
    PyIngestion,
    InputStream,
    ExtractionSession,
    NativeRegexEngine,
    CsvWriteStream,
)


class CustomTxtInputStream(InputStream[str, str]):
    def read(
        self, source: str, session: ExtractionSession | None = None
    ) -> Generator[str, None, None]:
        # For a directory: find files, or process directly
        import glob
        import os

        files = []
        if os.path.isdir(source):
            files = glob.glob(os.path.join(source, "*.txt"))
        elif os.path.isfile(source) and source.lower().endswith(".txt"):
            files = [source]

        self.total_units = len(files)
        self.current_unit_index = 0

        if session:
            session.start(self.total_units)

        for file_path in files:
            self.current_unit_index += 1
            if session:
                session.start_file(self.current_unit_index, file_path)

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            yield content

            if session:
                session.complete_file(self.current_unit_index)

        if session:
            session.complete()


# Inject it into PyIngestion orchestrator
input_stream = CustomTxtInputStream()
transform = NativeRegexEngine.from_file("rules.json")
output = CsvWriteStream("output.csv")

runner = PyIngestion()
runner.process(
    source="path/to/text/files",
    input_stream=input_stream,
    transform_stream=transform,
    output_stream=output,
)
```

#### Using Input Stream and Engine Components Directly

To parse files manually and match patterns page-by-page:

```python
from pyingestion import PdfInputStream, NativeRegexEngine

# 1. Setup the Regex engine with rules in-memory (dictionary)
regex_rules = {
    "infraction_id": {
        "regex": r"Código da Infração:\s*([A-Za-z0-9-]+)",
        "required": True,
    },
    "plate": {"regex": r"Placa:\s*([A-Z]{3}-?\d[A-Z0-9]\d{2})", "required": True},
}
engine = NativeRegexEngine(regex_rules)

# Alternatively, load rules from a JSON file path:
# engine = NativeRegexEngine.from_file("path/to/rules.json")

# 2. Setup the input stream
input_stream = PdfInputStream(pages_per_unit=1)

# 3. Process files programmatically
# The input stream yields raw text segments for each page/unit.
# You then parse it using the engine.
for raw_text in input_stream.read("path/to/infraction.pdf"):
    record = engine.transform(raw_text)
    print("Parsed Record:", record)
```

---

### 2. Command-Line Interface (CLI)

PyIngestion can be executed directly as a global shell command, as a python module run, or as a local script.

```bash
# 1. As a global command (after package installation)
pyingestion [options] [command] [command-options] ...

# 2. As a python module run (from the repository root)
python -m pyingestion [options] [command] [command-options] ...
```

#### Options
* `-s`, `--source` `<path>`: Input source path (file or directory).
* `-o`, `--output` `<path>`: Custom output file or database path (Default: `output.csv` in your working directory).
* `-g`, `--regex` `<path>`: Path to a JSON/TOML file containing customized regex extraction rules.
* `-r`, `--recursive`: Search for files recursively within subdirectories.
* `--resume`: Resume processing using checkpoint data from `.gaia_resume.json` in the current directory (does not require `--source`).
* `-t`, `--test` `<file_path>`: Test your regex rules on the first page of the provided file.
* `-p`, `--pages-per-unit` `<int>`: The number of pages/chunks grouped together as a single block for extraction matching (Default: `1`).
* `-l`, `--lang` `{"en", "pt"}`: Force the interface language to English or Portuguese (Default: `en`).
* `--type` `{"pdf", "docx", "ocr"}`: Define the built-in parser type to use (Default: `pdf`).
* `--to` `{"csv", "sqlite", "mysql"}`: Force output destination type (Default: `csv`).

#### Examples

* **Basic processing run**:
  ```bash
  pyingestion --source /path/to/pdfs -g rules.json
  ```

* **Resume an interrupted run**:
  ```bash
  pyingestion --resume
  ```

* **Test matching logic on a single file**:
  ```bash
  pyingestion -t sample.pdf -g rules.json
  ```

* **Run RAG embedding and ingestion via CLI Chaining**:
  ```bash
  pyingestion --source /path/to/pdfs pdf-input embed-transform --chunk-size 300 --chunk-overlap 50 --device cpu sqlite-vector-output --db vector_store.db
  ```

#### Configuration Files Layout

You can configure options and pipelines declaratively using a JSON or TOML file via the `-c` or `--config` parameter.

##### 1. Basic Configuration Format (Root level or [config] section)
To declare basic CLI options:
```toml
# config.toml
input_dir = "poc/pdfs"
output = "poc/resultados.csv"
regex = "poc/rules.toml"
to = "csv"
```
Or under a `[config]` section:
```toml
# config.toml
[config]
input_dir = "poc/pdfs"
output = "poc/resultados.csv"
regex = "poc/rules.toml"
```

##### 2. Advanced Declarative Pipelines
To define inputs, transforms, and outputs dynamically:
```toml
# pipeline.toml
input_dir = "poc/pdfs"

[input]
type = "pdf"
pages_per_unit = 2

[transform]
type = "regex"
config_file = "rules.toml"

[output]
type = "sqlite"
db_path = "records.db"
table_name = "pdf_records"
```

##### 3. RAG Declarative Ingestion Pipeline
To configure the document chunking, embedding, and vector database flow via a TOML config file:
```toml
# rag_pipeline.toml
input_dir = "poc/pdfs"

[input]
type = "pdf"

[transform]
type = "embed"
chunk_size = 300
chunk_overlap = 50
device = "cpu"

[output]
type = "sqlite-vector"
db_path = "vector_store.db"
table_name = "embeddings"
```
You can also define multiple transforms and outputs (e.g. to write to both CSV and SQLite):
```toml
# multi_pipeline.toml
input_dir = "poc/pdfs"

[input]
type = "pdf"

[[transform]]
type = "regex"
config_file = "rules.toml"

[[output]]
type = "sqlite"
db_path = "records.db"
table_name = "invoices"

[[output]]
type = "csv"
path = "backup.csv"
```

##### 4. Regex Extraction Rules (`rules.toml`)
Extraction rules can be defined using TOML (or JSON) format. Each section defines a field to extract, its regular expression pattern (optionally using a named capture group matching the section name), and whether the field is required for a successful extraction.

Here are two examples translated from `poc/rules.toml`:

**Example 1: Required date field**
```toml
[issue_date]
regex = 'Issue Date:\s*(?P<issue_date>\d{2}/\d{2}/\d{4})'
required = true
```

**Example 2: Optional text field**
```toml
[vehicle]
regex = 'Vehicle:\s*(?P<vehicle>.*?)\s{2,}Plate'
required = false
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
