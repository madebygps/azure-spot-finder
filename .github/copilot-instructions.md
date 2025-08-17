This repo is a small FastAPI PoC (spot-finder) that queries Azure for Spot-capable VM SKUs and exposes a minimal API.

Key points for an AI coding agent working in this repository

- How to run locally (developer workflow)
  - Create & activate a venv, install editable package (pyproject.toml is used):
    ```bash
    uv venv
    source .venv/bin/activate
    uv sync
    ```
  - Start the API server with uvicorn:
    ```bash
    uv run uvicorn backend.app.main:app --reload
    ```
  - Query example:
    ```bash
    curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus2'
    curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus2&raw=true'  # raw provider payload
    ```


- Code patterns & conventions specific to this repo
  - Absolute imports are used in `backend/app/main.py` (e.g. `from backend.app.azure_client import AzureSKUClient`) to allow running modules directly.
  - The Azure client returns plain Python dicts (not Pydantic models) for portability — the `filters` module shapes the response.
  - The `filters.filter_and_shape_items` function is the single place for dedupe, zone-union, filtering, pagination and shaping. Prefer changes there when altering response semantics.
  - Keep default behavior conservative: by default we filter for `supportsSpot==True` and exclude GPU SKUs unless `gpu=true` is passed.

- Integration points and external dependencies
  - Azure SDK: `azure-identity`, `azure-mgmt-compute`, `azure-mgmt-subscription`.
  - Cache: `cachetools.TTLCache` (short in-process cache used by `azure_client.py`).

- When editing code
  - Add unit tests for logic that manipulates the provider payload (use `output.json` as fixture in `tests/`).
  - Avoid network calls in unit tests — mock the Azure SDK or use `output.json` to exercise filtering/deduping.
  - Preserve the small, explicit API contract at `GET /v1/spot-skus`. If adding parameters, update `main.py` and `filters.py` together.

- Debugging tips
  - If import errors occur locally, ensure you run inside the venv and `uv sync` so local package imports resolve.
  - If `AZURE_SUBSCRIPTION_ID` discovery fails, check that the credential in your environment can list subscriptions (`az account show` / `az login`).

- Files to inspect for context
  - `backend/app/azure_client.py` — discovery, spot detection logic, SDK usage
  - `backend/app/main.py` — API surface and query params
  - `backend/app/filters.py` — dedupe, filter, shape, pagination
  - `backend/app/cache.py` — TTL cache details
  - `backend/README.md` — run instructions and prerequisites

If anything here is unclear or you want this shortened/expanded, tell me which section to iterate on and I will update the file.
