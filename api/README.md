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

Then query:

```bash
# Get spot SKUs without GPU instances (default)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus'

# Include GPU-enabled instances
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&gpu=true'

# Get only ARM64-based instances (Ampere Altra, Azure Cobalt 100)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&architecture=Arm64'

# Get only x64-based instances (Intel/AMD processors)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&architecture=x64'
```

## API Reference

### GET /v1/spot-skus

Returns a list of Azure VM SKUs that support spot instances for the specified region.

**Query Parameters:**

- `region` (required): Azure region name (e.g., 'eastus', 'westus2', 'eastus2')
- `gpu` (optional): Include GPU-enabled SKUs (default: false)
- `architecture` (optional): Filter by CPU architecture - 'x64' for Intel/AMD, 'Arm64' for ARM processors (default: all)
- `max_vcpus` (optional): Maximum vCPUs to include (default: 8)
- `max_memory_gb` (optional): Maximum memory in GB to include (default: 32.0)
- `include_pricing` (optional): Include spot pricing data (default: false)
- `include_eviction_rates` (optional): Include eviction rate data (default: false)
- `currency_code` (optional): Currency for pricing data (default: 'USD')

**Response Format:**

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

**Response Fields:**

- `name`: Full Azure SKU name
- `size`: SKU size identifier
- `family`: Azure SKU family name
- `has_gpu`: Whether the SKU includes GPU resources
- `architecture`: CPU architecture - 'x64' for Intel/AMD, 'Arm64' for ARM processors
- `vcpus`: Number of virtual CPU cores
- `memory_gb`: Memory allocation in gigabytes
- `zones`: Available Azure availability zones for this SKU in the region

**Error Responses:**

- `400`: Missing or invalid region parameter
- `500`: Azure API connection issues or internal server error

## Architecture & Directory Structure

The API follows clean architecture principles with clear separation of concerns:

```txt
api/
├── main.py                    # FastAPI application entry point and ASGI lifespan
├── README.md                  # This documentation
├── config/                    # Application configuration and dependency injection
│   └── dependencies.py       # DI container and FastAPI dependency functions
├── routes/                    # HTTP layer - API endpoints and request/response handling
│   └── sku_routes.py         # REST endpoints for spot SKU operations
├── services/                  # Business logic layer - core application logic
│   └── sku_service.py        # SKU filtering, GPU detection, and data transformation
├── clients/                   # Data access layer - Azure service integrations
│   ├── azure_client.py       # Centralized Azure authentication and core services
│   ├── compute_client.py     # Azure Compute Management for SKU operations
│   ├── pricing_client.py     # Azure Retail Prices API client
│   └── eviction_client.py    # Azure Resource Graph eviction rates client
└── utils/                     # Infrastructure utilities and cross-cutting concerns
    └── cache.py              # TTL caching utility for API responses
```

### Directory Responsibilities

#### `config/` - Application Configuration

- **`dependencies.py`**:
  - `DependencyContainer` class for managing singleton instances
  - FastAPI dependency functions (`provide_azure_client`, `provide_compute_client`, `provide_sku_service`)
  - Centralized dependency injection with concrete classes

#### `routes/` - HTTP Layer

- **`sku_routes.py`**:
  - REST API endpoints (`GET /v1/spot-skus`)
  - Request parameter validation and HTTP response handling
  - Dependency injection for service layer

#### `services/` - Business Logic

- **`sku_service.py`**:
  - Core application logic for SKU processing
  - Filtering (spot capability, GPU exclusion/inclusion)
  - Data transformation from Azure format to API format
  - Business rules and validation

#### `clients/` - Data Access Layer

- **`azure_client.py`**:
  - `AzureClient` class for centralized Azure authentication
  - Manages both sync and async credentials with token caching
  - Provides unified Azure service authentication interface

- **`compute_client.py`**:
  - `ComputeClient` class for Azure Compute Management operations
  - VM SKU discovery and technical specifications
  - Raw SKU data retrieval and Azure SDK integration

- **`pricing_client.py`**:
  - Integration with Azure Retail Prices API
  - Spot pricing data retrieval

- **`eviction_client.py`**:
  - Azure Resource Graph integration for eviction rates
  - Batch API operations for performance

#### `utils/` - Infrastructure Utilities

- **`cache.py`**:
  - TTL-based in-memory caching
  - Cache key generation and management
  - Performance optimization for repeated API calls

#### Root Files

- **`main.py`**:
  - FastAPI application initialization
  - ASGI lifespan management for dependency container
  - Router registration and server configuration

### Dependency Flow

The architecture follows clean dependency rules with centralized authentication:

```text
HTTP Request → routes/ → services/ → clients/ → Azure SDK
                ↓          ↓         ↓
            config/ ←    utils/   azure_client/
```

- **Routes** depend on services (business logic)
- **Services** depend on clients (data access) and utilities (caching)
- **Clients** use centralized Azure authentication and Azure SDK for data access
- **AzureClient** provides unified authentication for all Azure services
- **Config** orchestrates dependency injection
- **Utils** provide cross-cutting concerns (caching)
- **No circular dependencies** - ensures testability and maintainability

### Key Design Patterns

1. **Centralized Authentication**: Unified Azure credential management through `AzureClient`
2. **Service Layer**: Business logic separated from HTTP and data concerns
3. **Clean Architecture**: Dependencies point inward, business logic remains isolated
4. **TTL Caching**: Performance optimization with 30-minute cache expiration
5. **Fail-Fast DI**: Container errors are caught at startup rather than during request processing
6. **Type Safety**: Full type annotations for better developer experience and runtime safety
7. **Specialized Clients**: Domain-specific clients (`ComputeClient`, `PricingClient`, `EvictionClient`) with shared authentication

## How a Request Flows Through the System

When you make a request like `curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&gpu=true'`, here's what happens:

### 1. **Application Startup** (`main.py`)

- FastAPI app initializes with dependency container in `app.state`
- ASGI lifespan context manages startup/cleanup
- Container provides singleton instances for efficient resource usage

### 2. **HTTP Request** (`routes/sku_routes.py`)

- FastAPI routing matches `/v1/spot-skus?region=eastus&gpu=true`
- Dependency injection resolves `SkuService` instance
- Route validation ensures required parameters are present
- GPU parameter determines filtering behavior

### 3. **Business Logic** (`services/sku_service.py`)

- Service validates region parameter and GPU preference
- Checks cache for existing results (30-minute TTL)
- Delegates to compute client for fresh data if needed
- Applies business rules: spot capability, GPU inclusion/exclusion
- Returns structured data with metadata

### 4. **Data Access** (`clients/compute_client.py`)

- Compute client uses centralized Azure authentication from `AzureClient`
- Makes authenticated API call to Azure Compute Management
- Filters results at Azure level: `location eq 'eastus'`
- Returns raw Azure SDK objects to service layer

### 5. **Response Processing**

- Service processes raw Azure data with business logic
- Results cached for future requests
- FastAPI serializes response to JSON
- Client receives formatted spot SKU data

### Visual Request Flow

```text
curl request
    ↓
main.py (FastAPI app)
    ↓
routes/sku_routes.py (HTTP endpoint)
    ↓
config/dependencies.py (DI resolution)
    ↓
services/sku_service.py (business logic)
    ↓
utils/cache.py (cache check)
    ↓
┌─ CACHE HIT: return cached results ────┐
│                                       │
└─ CACHE MISS: continue ↓               │
   clients/compute_client.py (Azure SDK call)   │
       ↓                                │
   clients/azure_client.py (authentication)     │
       ↓                                │
   services/sku_service.py (filtering)  │
       ↓                                │
   utils/cache.py (cache store)         │
       ↓                                │
   ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←┘
routes/sku_routes.py (HTTP response)
    ↓
JSON response to client
```
