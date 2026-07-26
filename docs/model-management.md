# Model management and usage accounting

Convert2MD exposes a UI-independent Python API in `src.model_management`. CLI,
desktop and web layers should call this facade instead of reading SQLite or
calculating prices themselves. The public schema and event payload version is
`1.0`; the Python facade version is `v1`.

## State and security

The default database is
`$CONVERT2MD_STATE_DIR/model_management.sqlite3` (or
`~/.convert2md/model_management.sqlite3`). Schema migrations run on startup.
Providers store only references such as `env://GEMINI_API_KEY`. Configuration
imports reject fields named `api_key`, `token`, `secret`, or `password`; actual
credentials remain in environment variables or an operating-system secret
store.

`python convert2md.py models` prints the exact repository path followed by every
stored model, including imported, disabled and non-Gemini entries.

## Configuration

Import JSON or YAML with:

```shell
python convert2md.py models-import ./models.yaml
```

Example:

```yaml
schema_version: "1.0"
providers:
  - code: google
    display_name: Google AI
    adapter: google-genai
    secret_ref: env://GEMINI_API_KEY
models:
  - provider_code: google
    code: gemini-example
    display_name: Gemini Example
    context_window: 100000
    max_output_tokens: 8192
    capabilities: [text, vision, structured_output]
    rpm: 10
    tpm: 250000
    rpd: 100
    price:
      currency: USD
      input_per_million: "1.00"
      cached_input_per_million: "0.25"
      output_per_million: "4.00"
      image_each: "0"
      effective_from: "2026-01-01T00:00:00+00:00"
budgets:
  - scope: application
    amount: "25.00"
    currency: USD
    period: monthly
    warning_ratio: "0.8"
```

SQLite is the runtime source of truth after import. Prices are append-only.
Every usage record contains the exact price snapshot used for its cost, so
historical totals do not change when a new price is imported.

Google model codes must match the identifiers returned by the Gemini API
exactly. Version components use dots (for example,
`gemini-3.1-flash-lite`, not `gemini-3-1-flash-lite`). On startup the built-in
catalog adds currently supported diagram models and disables known obsolete or
malformed legacy entries. Provider quotas are account- and tier-dependent; edit
the local RPM/TPM/RPD planning limits to match the values shown for your project
in Google AI Studio.

## Application API

Create the facade with `create_model_management_api(state_dir)`. Its main
operations are:

- provider/model/price/budget writes and model queries;
- `validate_request(ModelRequest(...))` before a provider call;
- `register_usage(RegisterUsageCommand(...))` after every successful or failed
  provider attempt;
- `get_usage_summary(UsageQuery(...))` and `get_budget_status(scope)`;
- `get_form_schema("provider" | "model" | "budget")` for UI form metadata.

DTOs implement `to_dict()` and contain only JSON-compatible data. The FastAPI
adapter in `src/web_api.py` maps this facade to versioned `/api/v1/` resources
without moving business rules into controllers. The graphical interface uses
the same endpoints for catalog, price, budget and usage operations.

The CLI exposes `models`, `models-import`, `usage`, `usage-record`, and
`usage-import`. See [Web interface](web-interface.md) for the REST resource map
and graphical administration screens.

## Existing usage

Add one historical request:

```shell
python convert2md.py usage-record \
  --model google:gemini-3.1-flash-lite \
  --input-tokens 12000 \
  --output-tokens 800 \
  --operation document-conversion \
  --occurred-at 2026-07-20T14:30:00+03:00
```

Or import CSV, JSON, JSONL/NDJSON:

```shell
python convert2md.py usage-import ./usage.csv
```

The CSV header uses these fields:

```csv
model_id,operation,input_tokens,output_tokens,cached_input_tokens,reasoning_tokens,image_count,duration_ms,status,occurred_at,scope,document_id,provider_request_id,error_code,request_id
```

Only `model_id` is structurally required; omitted numeric fields default to
zero, `operation` defaults to `historical`, status to `success`, timestamp to
now, and scope to `application`. Model IDs must already exist in the repository.
Use stable `request_id` values when importing from another system: duplicates
are rejected and therefore cannot silently be counted twice.

Diagram-to-Mermaid conversion is integrated with this lifecycle. Preflight runs
before each Gemini attempt; successful and failed attempts are recorded
afterward. The existing quota ledger remains in place for RPM/TPM/RPD scheduling
and backward compatibility.
