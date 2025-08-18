# spot-finder

A FastAPI-based tool to discover Azure spot-capable VM SKUs by region.

## Overview

spot-finder is a minimal PoC that queries Azure for spot-capable VM SKUs and exposes them through a clean REST API. It provides efficient caching and filtering capabilities to help you find the right Azure spot instances for your workloads.

## Quick Start

### Prerequisites

- Python 3.13+
- Azure subscription with `AZURE_SUBSCRIPTION_ID` environment variable
- Azure authentication via `DefaultAzureCredential` (Azure CLI, managed identity, or service principal)

### Installation & Running

```bash
# Clone and setup
git clone <repository-url>
cd spot-finder

# Install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# Start the API server
uv run uvicorn api.main:app --reload
```

### Usage Examples

```bash
# Get all spot-capable SKUs for East US (excludes GPU instances by default)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus'

# Include GPU-enabled instances
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&gpu=true'

# Try different regions
curl 'http://127.0.0.1:8000/v1/spot-skus?region=westus2'
```

## API Documentation

Once running, visit <http://127.0.0.1:8000/> for interactive API documentation.

### Key Endpoint: `GET /v1/spot-skus`

**Parameters:**

- `region` (required): Azure region (e.g., 'eastus', 'westus2')
- `gpu` (optional): Include GPU SKUs (default: false)

**Response:**

```json
{
  "items": [
    {
      "name": "Standard_D2s_v3",
      "size": "D2s_v3",
      "family": "standardDSv3Family",
      "has_gpu": false,
      "vcpus": 2,
      "memory_gb": 8,
      "zones": ["1", "2", "3"]
    }
  ],
  "metadata": {
    "region": "eastus",
    "include_gpu": false,
    "count": 245
  }
}
```

## Architecture

Built with clean architecture principles:

- **Routes** (`api/routes/`): HTTP endpoints and request handling
- **Services** (`api/services/`): Business logic and data transformation
- **Clients** (`api/clients/`): Azure SDK integration
- **Config** (`api/config/`): Dependency injection
- **Utils** (`api/utils/`): Caching and utilities

Features 30-minute TTL caching for performance and dependency injection for clean testability.

## Development

See [`api/README.md`](api/README.md) for detailed development information, architecture details, and contribution guidelines.

## License

See [LICENSE](LICENSE) file.
