# spot-finder PoC backend

Minimal PoC that lists spot-capable VM SKUs per region.

Prerequisites

- Python 3.13
- An Azure subscription id in `AZURE_SUBSCRIPTION_ID` env var
- Login credentials available for `DefaultAzureCredential` (Managed Identity or env vars AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)

Install deps and run (recommended in a venv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .  # or pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Then query:

```bash
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus'
```
