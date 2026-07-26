# Convert2MD

Convert2MD converts PDF, DOCX and DOC documents to Markdown, extracts images,
converts embedded vector graphics, and can recognize PNG/JPG diagrams as
Mermaid. The application is available through both a CLI and a local graphical
web interface.

The project also contains a UI-independent subsystem for managing AI providers,
models, limits, prices, budgets and usage accounting.

## Main features

- PDF conversion through Docling.
- DOCX/DOC conversion through Pandoc.
- Image extraction into portable `picture_<document>/` directories.
- EMF/WMF conversion to PNG through LibreOffice Draw, with Inkscape and
  ImageMagick fallbacks.
- Diagram-to-Mermaid conversion through configured vision models.
- Single-file and batch processing.
- Local graphical web interface.
- SQLite-backed model catalog and usage history.
- Preflight validation, prices, price snapshots and budgets.
- YAML/JSON configuration import and CSV/JSON/JSONL usage import.
- Secret references such as `env://GEMINI_API_KEY`; secrets are not stored in
  configuration or SQLite.

## Requirements

- Python 3.10 or newer.
- Pandoc for DOCX/DOC conversion.
- LibreOffice is recommended for EMF/WMF conversion.
- Inkscape or ImageMagick can be used as fallback converters.
- Node.js 22.13 or newer to build the web interface.

Install Python dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Build the web interface once:

```bash
cd web
npm install
npm run build
cd ..
```

## Graphical interface

Start the complete local application:

```bash
venv/bin/python convert2md.py web
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

The interface provides:

- PDF, DOCX and DOC conversion;
- multi-file conversion;
- ZIP downloads containing Markdown and extracted images;
- image-to-Mermaid conversion;
- provider and model management;
- technical limits and capabilities;
- prices and budgets;
- manual usage registration;
- configuration and historical usage import;
- usage, token and cost summaries.

All data, documents and provider credentials remain on the local machine. See
[Web interface](docs/web-interface.md) for the full description.

## CLI examples

Convert one document:

```bash
python convert2md.py convert report.pdf
python convert2md.py convert document.docx --output document.md
```

Convert a directory:

```bash
python convert2md.py batch ./documents --recursive
```

Convert a diagram to Mermaid:

```bash
export GEMINI_API_KEY="..."
python convert2md.py diagram ./diagram.png
python convert2md.py diagrams ./images --plan-only
```

Inspect or import the model catalog:

```bash
python convert2md.py models
python convert2md.py models-import ./models.yaml
```

Review and register usage:

```bash
python convert2md.py usage
python convert2md.py usage-record \
  --model google:gemini-3.1-flash-lite \
  --input-tokens 12000 \
  --output-tokens 800 \
  --operation document-conversion
python convert2md.py usage-import ./usage.csv
```

List every command:

```bash
python convert2md.py --help
```

## Output

A regular conversion produces a Markdown file and a neighboring image
directory:

```text
documents/
├── report.pdf
├── report.md
└── picture_report/
    ├── image_001.png
    └── image_002.png
```

Links in the Markdown output are relative, so the Markdown file and its
`picture_*` directory can be moved together.

## Model and usage state

The default application state is stored in:

```text
~/.convert2md/
├── model_management.sqlite3
└── quota.sqlite3
```

Set `CONVERT2MD_STATE_DIR` to use another directory. SQLite is the runtime
source of truth after configuration import. Provider credentials are addressed
only through `secret_ref`.

See [Model management and usage accounting](docs/model-management.md).

## Documentation

- [Documentation index](docs/index.md)
- [Quick start](docs/quickstart.md)
- [Web interface](docs/web-interface.md)
- [Model management and usage accounting](docs/model-management.md)
- [Architecture](docs/architecture.md)
- [Vector graphics and EMF/WMF safety](docs/vector-graphics.md)
- [Document conversion requirements](docs/change-requirements.md)
- [Contributing](docs/contributing.md)
- [Changelog](docs/changelog.md)
- [Raw Inkscape 1.4.4 crash report](docs/diagnostics/inkscape-1.4.4-crash.txt)

## Tests

Run the Python suite:

```bash
venv/bin/python -m pytest -q
```

Validate the web build:

```bash
cd web
npm run build
```

## Project layout

```text
Convert2MD/
├── src/                    Python application and REST API
│   └── model_management/   Model catalog and usage subsystem
├── web/                    Graphical web interface
├── tests/                  Automated tests
├── docs/                   Project documentation
├── convert2md.py           CLI entry point
├── web_server.py           Direct web server entry point
└── README.md               Project overview and documentation links
```
