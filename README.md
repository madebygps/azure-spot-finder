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

# Get only ARM64-based instances (Ampere Altra, Azure Cobalt 100)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&architecture=Arm64'

# Get only x64-based instances (Intel/AMD processors)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&architecture=x64'

# Get intelligent recommendations (top 5 cost-optimized)
curl 'http://127.0.0.1:8000/v1/spot-recommendations?region=eastus&optimize_for=cost'

# Get reliability-focused recommendations with cost constraint
curl 'http://127.0.0.1:8000/v1/spot-recommendations?region=eastus&optimize_for=reliability&max_hourly_cost=0.05'

# Try different regions
curl 'http://127.0.0.1:8000/v1/spot-skus?region=westus2'
```

## API Documentation

Once running, visit <http://127.0.0.1:8000/> for interactive API documentation.

### Key Endpoints

#### `GET /v1/spot-skus` - List Spot SKUs

Returns all spot-capable VM SKUs for a region with optional filtering.

#### `GET /v1/spot-recommendations` - Smart Recommendations

**NEW!** Returns top-ranked spot instance recommendations based on intelligent scoring that considers:

- **Price optimization** - Lower costs score higher
- **Reliability** - Lower eviction rates score higher
- **Performance** - Better price/performance ratios score higher
- **Availability** - More availability zones score higher
- **Architecture preferences** - ARM64 vs x64 preferences

**Example Optimization Strategies:**
- `optimize_for=cost` - Best bang for buck
- `optimize_for=reliability` - Lowest eviction risk
- `optimize_for=performance` - Best price/performance
- `optimize_for=balanced` - Balanced scoring (default)

**Parameters:**

- `region` (required): Azure region (e.g., 'eastus', 'westus2')
- `gpu` (optional): Include GPU SKUs (default: false)
- `architecture` (optional): Filter by CPU architecture - 'x64' for Intel/AMD, 'Arm64' for ARM processors (default: all)
- `max_vcpus` (optional): Maximum vCPUs (default: 8)
- `max_memory_gb` (optional): Maximum memory in GB (default: 32.0)
- `include_pricing` (optional): Include spot pricing data (default: false)
- `include_eviction_rates` (optional): Include eviction rate data (default: false)
- `currency_code` (optional): Currency for pricing (default: 'USD')

**Response:**

```json
{
  "items": [
    {
      "name": "Standard_D2s_v3",
      "size": "D2s_v3",
      "family": "standardDSv3Family",
      "has_gpu": false,
      "architecture": "x64",
      "vcpus": 2,
      "memory_gb": 8,
      "zones": ["1", "2", "3"]
    }
  ],
  "metadata": {
    "region": "eastus",
    "include_gpu": false,
    "architecture": null,
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
