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

## What Can We Do With This Data?

The spot-finder API provides rich data that enables powerful automation and cost optimization workflows. Here are practical applications:

### 💰 Cost Optimization & Monitoring

#### Automated Cost Analysis

```bash
# Compare costs across regions to find the cheapest spot instances
for region in eastus westus2 centralus; do
  echo "=== $region ==="
  curl -s "http://localhost:8000/v1/spot-recommendations?region=$region&optimize_for=cost&include_pricing=true" | jq '.items[0:3]'
done
```

#### Price Alerts & Notifications

- Set up scheduled jobs to monitor spot price changes
- Trigger Slack/email notifications when prices drop below thresholds
- Create cost tracking dashboards with historical price data

### 🚀 Infrastructure Automation

#### Terraform/ARM Template Generation

```python
# Example: Generate Terraform configuration from API response
import requests
import json

response = requests.get('http://localhost:8000/v1/spot-recommendations?region=eastus&optimize_for=cost')
recommendations = response.json()['items']

for vm in recommendations[:3]:
    print(f"""
resource "azurerm_linux_virtual_machine" "{vm['size'].lower()}_spot" {{
  name                = "vm-{vm['size'].lower()}-spot"
  resource_group_name = var.resource_group_name
  location            = "East US"
  size                = "{vm['name']}"
  priority            = "Spot"
  eviction_policy     = "Deallocate"

  # Configuration based on {vm['vcpus']} vCPUs, {vm['memory_gb']}GB RAM
}}""")
```

#### CI/CD Pipeline Integration

- Automatically select optimal spot instances for ephemeral build agents
- Integrate with GitHub Actions, Azure DevOps, or Jenkins for dynamic scaling
- Choose different VM sizes based on workload requirements (CPU vs memory intensive)

### 🏗️ Multi-Region Deployment Strategies

#### High Availability Planning

```bash
# Find reliable instances across multiple regions for redundancy
curl -s 'http://localhost:8000/v1/spot-recommendations?region=eastus&optimize_for=reliability&include_eviction_rates=true'
curl -s 'http://localhost:8000/v1/spot-recommendations?region=westus2&optimize_for=reliability&include_eviction_rates=true'
```

#### Global Load Balancing

- Deploy workloads across regions with the lowest eviction rates
- Automatically failover to backup regions when spot capacity is low
- Balance cost vs reliability across geographic locations

### 🤖 Machine Learning & AI Workloads

#### GPU Instance Discovery

```bash
# Find the most cost-effective GPU instances for ML training
curl 'http://localhost:8000/v1/spot-recommendations?region=eastus&gpu=true&optimize_for=cost&include_pricing=true'
```

#### Training Job Optimization

- Automatically pause/resume training jobs based on spot availability
- Choose between different GPU SKUs (V100, A100, etc.) based on cost and performance
- Implement checkpointing strategies based on eviction rate data

### 📊 Business Intelligence & Reporting

#### Cost Forecasting

- Analyze historical pricing trends to predict future costs
- Generate monthly/quarterly spot instance spending reports
- Compare actual vs potential savings from spot usage

#### Architecture Decision Support

- Choose between ARM64 (Cobalt, Ampere) vs x64 instances based on workload compatibility
- Evaluate trade-offs between different VM families (compute vs memory optimized)
- Support procurement decisions with data-driven cost analysis

### 🔄 DevOps Automation Patterns

#### Auto-Scaling Integration

```bash
# Example: Scale Kubernetes nodes with optimal spot instances
kubectl scale deployment app --replicas=0  # Scale down
# API call to get current best spot instance
NEW_VM_SIZE=$(curl -s 'http://localhost:8000/v1/spot-recommendations?region=eastus&optimize_for=balanced' | jq -r '.items[0].name')
# Update node pool with new VM size
az aks nodepool update --name spot-pool --cluster-name my-cluster --node-vm-size $NEW_VM_SIZE
```

#### Disaster Recovery Planning

- Pre-identify backup VM sizes in case primary spot instances become unavailable
- Create runbooks for switching between different spot instance types
- Monitor eviction rates to proactively migrate workloads

### 📈 Advanced Analytics Use Cases

#### Performance Benchmarking

- Correlate VM specifications with application performance metrics
- A/B test different instance types for optimal price/performance ratios
- Track ARM64 vs x64 performance differences for your specific workloads

#### Capacity Planning

- Monitor availability zone distribution to avoid single points of failure
- Plan workload distribution based on regional spot capacity
- Optimize data locality by choosing instances in zones near your storage

### 🛠️ Integration Examples

The API can be integrated with various tools and platforms:

- **Monitoring**: Grafana dashboards, Azure Monitor, DataDog
- **Automation**: Azure Logic Apps, AWS Lambda, Google Cloud Functions
- **ChatOps**: Slack bots, Microsoft Teams integrations
- **Infrastructure**: Pulumi, CDK, Ansible playbooks
- **Containers**: Kubernetes cluster autoscaler, Docker Swarm, ACI

By leveraging this data programmatically, you can achieve significant cost savings (often 60-90% compared to on-demand pricing) while maintaining operational efficiency and reliability.

## Architecture

Built with clean architecture principles:

- **Routes** (`api/routes/`): HTTP endpoints and request handling
- **Services** (`api/services/`): Business logic and data transformation
- **Clients** (`api/clients/`): Azure SDK integration
- **Config** (`api/config/`): Dependency injection
- **Utils** (`api/utils/`): Caching and utilities

Features 30-minute TTL caching for performance and dependency injection for clean testability.

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

## Development

See [`api/README.md`](api/README.md) for detailed development information, architecture details, and contribution guidelines.

## License

See [LICENSE](LICENSE) file.
