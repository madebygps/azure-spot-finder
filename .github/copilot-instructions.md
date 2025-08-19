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
    uv run uvicorn api.main:app --reload
    ```
  - Query example:
    ```bash
    # Get spot SKUs without GPU instances (default)
    curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus'

    # Include GPU-enabled instances
    curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&gpu=true'
    ```


- Code patterns & conventions specific to this repo
  - The app is organized into logical folders: `config/` (DI container), `clients/` (Azure service integrations), `routes/`, `services/` (business logic), `utils/` (cache, utilities)
  - Absolute imports are used (e.g. `from api.clients.compute_client import ComputeClient`) to allow running modules directly.
  - Centralized Azure authentication: `AzureClient` provides unified credential management, while specialized clients (`ComputeClient`, `PricingClient`, `EvictionClient`) handle domain-specific operations.
  - The clients return raw Python objects from the Azure SDK - the service layer handles all business logic, filtering, and data transformation.
  - Dependency injection is used throughout with FastAPI's dependency system and a custom container pattern.
  - Keep default behavior conservative: by default we filter for `supportsSpot==True` and exclude GPU SKUs unless `gpu=true` is passed.

- Integration points and external dependencies
  - Azure SDK: `azure-identity`, `azure-mgmt-compute`, `azure-mgmt-subscription`.
  - Cache: `cachetools.TTLCache` (short in-process cache used by `utils/cache.py`).
  - FastAPI: Dependency injection, lifespan events, router inclusion.

- When editing code
  - Add unit tests for logic that manipulates the provider payload. Currently no tests directory exists but pytest is configured.
  - Avoid network calls in unit tests — mock the Azure SDK and `AzureClient` when creating tests.
  - Preserve the small, explicit API contract at `GET /v1/spot-skus`. If adding parameters, update `api/routes/sku_routes.py` and `api/services/sku_service.py` together.
  - When adding new Azure service integrations, use the centralized `AzureClient` for authentication rather than creating new credentials.

- Debugging tips
  - If import errors occur locally, ensure you run inside the venv and `uv sync` so local package imports resolve.
  - If `AZURE_SUBSCRIPTION_ID` discovery fails, check that the credential in your environment can list subscriptions (`az account show` / `az login`).
  - Authentication issues are centralized in `AzureClient` - check credential provider setup first.
  - For Azure API errors, verify that the Azure credentials have appropriate permissions for the specific service (Compute, Resource Graph, etc.).

- Files to inspect for context
  - `api/clients/azure_client.py` — centralized Azure client for authentication and core Azure services
  - `api/clients/compute_client.py` — Azure Compute Management client for SKU operations and VM data
  - `api/services/sku_service.py` — business logic for spot detection, filtering, GPU detection, data transformation
  - `api/routes/sku_routes.py` — API endpoints and query parameter handling
  - `api/utils/cache.py` — TTL cache details
  - `api/README.md` — run instructions and prerequisites
