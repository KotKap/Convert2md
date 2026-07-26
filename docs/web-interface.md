# Graphical web interface

Convert2MD includes a local graphical interface in `web/` and a FastAPI backend
in `src/web_api.py`. Both parts are started by one CLI command.

## Build

The frontend must be built once after checkout or after changing its source:

```bash
cd web
npm install
npm run build
cd ..
```

Requirements:

- Node.js 22.13 or newer;
- installed Python dependencies from `requirements.txt`.

## Start

```bash
venv/bin/python convert2md.py web
```

Open `http://127.0.0.1:3000`. The frontend uses port 3000 and the local REST API
uses port 8000. Press `Ctrl+C` in the launching terminal to stop both.
The combined command also loads `GEMINI_API_KEY` from the project `.env` file.
Opening the page as either `localhost` or `127.0.0.1`, including on a custom
local UI port, is supported.

## Sections

### Overview

Shows:

- configured model and provider counts;
- successful and failed request counts;
- input and output token totals;
- accumulated cost;
- usage distribution by model;
- physical path of the SQLite repository.

### Conversion

Supports:

- PDF, DOCX and DOC documents;
- multiple files in one operation;
- optional noise-filter disabling;
- PNG/JPG diagram recognition through a selected vision model;
- downloadable Markdown;
- ZIP output when a document contains extracted images.

The ZIP contains the Markdown document and its `picture_*` resources, preserving
relative links.

The diagram selector shows only active Google models with vision support.
`gemini-3.1-flash-lite` is the default. Deprecated or malformed legacy model
records remain visible in the administrative catalog, but cannot be selected
for conversion.

### Catalog

Provides forms and lists for:

- providers and their adapters;
- masked secret references;
- models and display names;
- context and output limits;
- RPM, TPM and RPD quotas;
- capabilities and model status.

### Accounting

Provides:

- current prices;
- input, cached-input, output and image rates;
- daily, monthly or total budgets;
- manual historical usage registration;
- usage and cost summaries.

Historical usage applies the price effective at `occurred_at`, and the resulting
usage record retains that price snapshot.

### Import

Supports:

- YAML/JSON provider, model, price and budget configuration;
- CSV, JSON and JSONL/NDJSON usage history;
- validation before persistence;
- rejection of embedded `api_key`, `token`, `secret` and `password` fields.

## Local REST API

The backend is versioned under `/api/v1/`. Principal resources:

```text
GET/POST /api/v1/providers
GET/POST /api/v1/models
GET/POST /api/v1/prices
GET/POST /api/v1/budgets
GET/POST /api/v1/usage
POST     /api/v1/config/import
POST     /api/v1/usage/import
POST     /api/v1/convert/document
POST     /api/v1/convert/diagram
GET      /api/v1/dashboard
GET      /api/v1/health
```

The API delegates model, budget, pricing and usage rules to
`ModelManagementAPI`; controllers do not duplicate domain logic.

## Deployment model

The interface is intentionally local. Document conversion depends on the local
filesystem, SQLite, Pandoc, Docling, LibreOffice and provider credentials.
Publishing only the frontend would produce a non-functional shell without
access to those services.
