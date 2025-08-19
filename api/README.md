# spot-finder PoC API

Minimal PoC that lists Azure spot-capable VM SKUs per region using a clean, layered architecture.

## Prerequisites

- Python 3.13
- An Azure subscription id in `AZURE_SUBSCRIPTION_ID` env var
- Login credentials available for `DefaultAzureCredential` (Managed Identity or env vars AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)

## Quick Start

Install deps and run (recommended in a venv):

```bash
uv venv
source .venv/bin/activate
uv sync
uv run uvicorn api.main:app --reload
```

Then query or use Swagger UI main page:

```bash
# Get spot SKUs without GPU instances (default)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus'

# Include GPU-enabled instances
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&gpu=true'

# Get only ARM64-based instances (Ampere Altra, Azure Cobalt 100)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&architecture=Arm64'

# Get only x64-based instances (Intel/AMD processors)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&architecture=x64'

# Get intelligent recommendations (top 5 cost-optimized)
curl 'http://127.0.0.1:8000/v1/spot-recommendations?region=eastus&optimize_for=cost'

# Get reliability-focused recommendations with constraints
curl 'http://127.0.0.1:8000/v1/spot-recommendations?region=eastus&optimize_for=reliability&max_hourly_cost=0.05&max_eviction_rate=5-10'
```

## Contributing

This is very much a PoC and WIP. Feel free to open issues or PRs with improvements or suggestions.
