# spot-finder

A FastAPI-based tool to discover Azure spot-capable VM SKUs by region.

## Overview

The API solves the pain point of manually hunting through the Azure portal for spot instances. Instead of clicking through dozens of VM sizes to find spot-capable instances, developers can query the API and get comprehensive data in seconds.

## Quick Start

### Prerequisites

- Python 3.13+
- Azure subscription with `AZURE_SUBSCRIPTION_ID` environment variable
- Azure authentication via `DefaultAzureCredential` (Azure CLI, managed identity, or service principal)

### Installation & Running

#### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd spot-finder
```

#### Step 2: Set Up Environment Variables

```bash
# Copy the environment sample file
cp .env.sample .env

# Edit .env file and add your Azure subscription ID
# Required: AZURE_SUBSCRIPTION_ID=your-subscription-id-here
```

#### Step 3: Create Python Virtual Environment

```bash
uv venv
```

#### Step 4: Activate Virtual Environment

```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

#### Step 5: Install Dependencies

```bash
uv sync
```

#### Step 6: Start the API Server

```bash
uv run uvicorn api.main:app --reload
```

The API will be available at <http://127.0.0.1:8000/> with interactive documentation.

### Usage Examples

```bash
# Get all spot-capable SKUs for East US (excludes GPU instances by default)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus'

# Include GPU-enabled instances
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&gpu=true'

# Get only ARM64-based instances (Ampere Altra, Azure Cobalt 100)
curl 'http://127.0.0.1:8000/v1/spot-skus?region=eastus&architecture=Arm64'

# Get reliability-focused recommendations with cost constraint
curl 'http://127.0.0.1:8000/v1/spot-recommendations?region=eastus&optimize_for=reliability&max_hourly_cost=0.05'

# Try different regions
curl 'http://127.0.0.1:8000/v1/spot-skus?region=westus2'
```

## Known Limitations and Implementation Notes

### Architecture Detection

The tool determines CPU architecture (x64 vs ARM64) using **hardcoded naming pattern matching** rather than querying Azure SDK metadata directly. This is a pragmatic workaround for the current Azure SDK limitations:

- **ARM64 Detection**: Looks for specific patterns in SKU names like `pls`, `pds`, `ps_`, `eps`, `epds` (e.g., Dplsv5, Dpsv6, Epsv5)
- **x64 Detection**: Falls back to x64 for all other SKUs (Ds, Es, Fs, etc.)

**Implementation location**: `api/clients/compute_client.py` in `_extract_sku_specs()`

**Potential improvements**: This approach works reliably for current Azure SKU naming conventions, but could break if Microsoft changes their naming patterns. A more robust solution would query Azure's hardware profile APIs directly when such APIs become available.

### Eviction Rate Data Source

Spot VM eviction rates are obtained by **replicating the same Azure Resource Graph query that the Azure Portal uses** rather than through an official public API:

- **Data source**: Azure Resource Graph `SpotResources` table via batch API
- **Query**: Uses the same KQL query that powers the Azure Portal's spot instance eviction rate displays
- **Authentication**: Requires standard Azure Management API permissions

**Implementation location**: `api/clients/eviction_client.py`

**Important considerations**:

- This approach provides the same data users see in the Azure Portal
- The query structure could potentially change if Microsoft updates their internal portal implementation
- No official public API exists specifically for eviction rate data as of this implementation
- Rate limiting applies per Azure's standard Resource Graph quotas

**Potential improvements**: Monitor for official Azure APIs that expose eviction rate data directly. Microsoft may provide dedicated endpoints for this data in the future.

### Authentication Requirements

The tool requires Azure credentials with permissions for:

- **Compute Management API**: To list VM SKUs and capabilities
- **Resource Graph API**: To query spot eviction rates
- **Retail Prices API**: For pricing data (when enabled)

Users must ensure their Azure credentials (via Azure CLI, managed identity, or service principal) have appropriate permissions for these services.

## Recomendation Service

At the moment this is hard coded to return the top 5 recommendations based on a simple scoring algorithm that considers:

- **Price**: Lower costs score higher
- **Eviction Rate**: Lower eviction rates score higher
- **Performance**: Better price/performance ratios score higher
- **Availability**: More availability zones score higher
- **Architecture Preferences**: ARM64 vs x64 preferences

You could fork and adapt the recommendation logic to suit your specific needs.

## SKU data filtering

I chose to filter only the most relevant SKUs for spot usage but you can adjust the filtering logic in `api/routes/compute_client.py` to include whatever info you need from the ComputeManagementClient.

## Development

See [`api/README.md`](api/README.md) for detailed development information, architecture details, and contribution guidelines.

## License

See [LICENSE](LICENSE) file.
