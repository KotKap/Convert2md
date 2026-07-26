# Convert2MD architecture

## Overview

Convert2MD consists of five cooperating layers:

```text
CLI ───────────────┐
Graphical web UI ──┼── Application services ── Conversion/model domains
REST API ──────────┘              │
                                  ├── SQLite state
                                  ├── Pandoc / Docling
                                  └── AI provider adapters
```

The CLI and web interface share the same conversion and model-management
services. Business rules are not implemented in UI controllers.

## Repository structure

```text
Convert2MD/
├── src/
│   ├── cli.py                    Typer CLI and local web launcher
│   ├── web_api.py                FastAPI REST adapter
│   ├── converter.py              Converter factory and orchestration
│   ├── converter_strategy.py     Converter interface
│   ├── pdf_converter.py          PDF conversion through Docling
│   ├── docx_converter.py         DOCX/DOC conversion through Pandoc
│   ├── diagram_converter.py      Diagram-to-Mermaid service
│   ├── diagram_models.py         Diagram planning and built-in limits
│   ├── quota.py                  RPM/TPM/RPD ledger and throttling
│   └── model_management/
│       ├── domain.py             Providers, models, prices and budgets
│       ├── dto.py                Serializable v1 commands and DTOs
│       ├── facade.py             UI-independent application API
│       ├── repository.py         SQLite repositories and migrations
│       ├── config_import.py      YAML/JSON configuration import
│       ├── usage_import.py       CSV/JSON/JSONL usage import
│       └── bootstrap.py          Composition root and built-in catalog
├── web/                          React/vinext graphical interface
├── tests/                        Automated tests
├── docs/                         Project documentation
├── convert2md.py                 Main CLI entry point
└── web_server.py                 Direct web server entry point
```

## Document conversion

### Strategy and factory

`ConverterStrategy` defines the common converter contract. `ConverterFactory`
selects `PDFConverter` or `DOCXConverter` by file extension.

```text
input file
   │
   ▼
DocumentConverter
   │
   ▼
ConverterFactory
   ├── PDFConverter
   └── DOCXConverter
   │
   ▼
Markdown + metadata + picture_<document>/
```

### PDF

`PDFConverter` uses Docling and PyMuPDF to:

- extract text and document structure;
- extract pictures;
- replace image placeholders;
- preserve tables and formulas where possible;
- filter page noise;
- post-process Markdown.

### DOCX/DOC

`DOCXConverter` uses Pandoc to:

- produce GitHub-flavored Markdown;
- extract embedded media;
- flatten Pandoc's nested `media/` directory;
- rewrite image links to portable relative paths;
- convert EMF/WMF graphics to PNG.

Vector conversion order:

1. headless LibreOffice Draw;
2. Inkscape;
3. ImageMagick;
4. preserve the original vector file.

See [Vector graphics and EMF/WMF safety](vector-graphics.md).

## Diagram conversion

`ImageMermaidConverter`:

1. estimates image tokens;
2. performs model-management preflight validation;
3. waits for local RPM/TPM capacity;
4. calls the provider adapter;
5. validates returned Mermaid;
6. writes Markdown atomically;
7. records successful or failed usage.

`BatchPlanner` distributes images across configured Gemini models according to
RPD capacity and supports fallback replanning.

## Model management

`ModelManagementAPI` is the stable UI-independent facade. It provides:

- providers and secret references;
- model capabilities and technical limits;
- current and historical prices;
- preflight validation and cost estimation;
- immutable price snapshots on usage records;
- budgets and budget status;
- usage registration and summaries;
- configuration and historical usage import;
- form metadata for different UI technologies.

SQLite is the runtime source of truth. YAML and JSON are transport and bootstrap
formats, not competing state stores.

See [Model management](model-management.md).

## Web application

The local graphical interface has two processes started by one command:

```text
browser :3000 ──► React/vinext UI
                     │
                     ▼
                FastAPI :8000
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
     converters   facade      SQLite
```

`src/web_api.py` exposes versioned `/api/v1/` endpoints. The React interface
provides overview, conversion, catalog, accounting and import sections.

The web application remains local because conversion requires filesystem
access, native tools, SQLite and provider credentials.

See [Web interface](web-interface.md).

## Persistence

Default state:

```text
~/.convert2md/
├── model_management.sqlite3
└── quota.sqlite3
```

`CONVERT2MD_STATE_DIR` overrides the directory.

`model_management.sqlite3` stores normalized providers, models, prices, budgets
and usage. `quota.sqlite3` remains a compatibility ledger for short-term and
daily diagram scheduling.

## Security

- Provider secrets are never stored in the catalog.
- Providers contain only `secret_ref`, for example
  `env://GEMINI_API_KEY`.
- Configuration import rejects common plaintext secret fields.
- The web server binds to `127.0.0.1` by default.
- Uploaded web documents are handled in temporary directories.
- Temporary conversion data is deleted after the response is prepared.

## Extension points

### New document format

1. Implement `ConverterStrategy`.
2. Register the converter in `ConverterFactory`.
3. Add CLI/web format validation.
4. Add unit and integration tests.

### New model provider

1. Add a provider adapter.
2. Register provider/model data through `ModelManagementAPI`.
3. Map provider usage metadata into `RegisterUsageCommand`.
4. Add preflight and failure-mapping tests.

### New UI

Use `ModelManagementAPI` directly for an embedded Python UI, or consume the
versioned REST endpoints. UI code must not calculate prices or write SQLite
directly.

## Testing

The suite covers:

- document post-processing and converter selection;
- EMF validation and safe converter order;
- quota planning and retries;
- model preflight, cost snapshots and budgets;
- configuration and usage import;
- REST catalog, accounting and security behavior.

Run:

```bash
venv/bin/python -m pytest -q
```

Build validation for the web interface:

```bash
cd web
npm run build
```

## Related documentation

- [Project README](../README.md)
- [Web interface](web-interface.md)
- [Model management](model-management.md)
- [Vector graphics](vector-graphics.md)
- [Contributing](contributing.md)
