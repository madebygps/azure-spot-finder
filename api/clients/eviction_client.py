"""Azure Spot VM eviction rate client using batch API."""
import logging
from typing import Dict, List, Optional
import httpx
from api.clients.azure_client import AzureClient

logger = logging.getLogger(__name__)


class EvictionClient:
    """Client for fetching Azure Spot VM eviction rates using the batch API.

    Authentication is handled by the injected AzureClient.
    """

    def __init__(self, azure_client: AzureClient):
        """Initialize eviction client with Azure client.

        Args:
            azure_client: Centralized Azure client for authentication
        """
        self.azure_client = azure_client

    async def _get_access_token(self) -> str:
        """Get Azure access token for management API.

        Token caching is handled by the Azure client.
        """
        return await self.azure_client.get_management_token()

    async def get_eviction_rates(
        self,
        sku_names: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Fetch eviction rates for specified SKUs and locations.

        Args:
            sku_names: List of SKU names to query (e.g., ['standard_d2s_v4'])
            locations: List of Azure regions (e.g., ['eastus', 'westus'])

        Returns:
            Dict with structure: {sku_name: {location: eviction_rate}}
            Example: {'standard_d2s_v4': {'eastus': '0-5', 'westus': '5-10'}}
        """
        try:
            # Build the KQL query
            query = "SpotResources | where type =~ 'microsoft.compute/skuspotevictionrate/location'"

            # Add filters if specified
            if sku_names:
                sku_filter = "', '".join(sku_names)
                query += f" | where sku.name in~ ('{sku_filter}')"

            if locations:
                location_filter = "', '".join(locations)
                query += f" | where location in~ ('{location_filter}')"

            query += " | project skuName = tostring(sku.name), location, spotEvictionRate = tostring(properties.evictionRate)"
            query += " | order by skuName asc, location asc"

            # Prepare batch request payload
            batch_payload = {
                "requests": [
                    {
                        "content": {
                            "query": query,
                            "options": {
                                "$top": 1000,
                                "$skip": 0,
                                "$skipToken": "",
                                "resultFormat": "table",
                            },
                        },
                        "httpMethod": "POST",
                        "name": "eviction-rates-query",
                        "requestHeaderDetails": {
                            "commandName": "SpotFinder.EvictionRateQuery"
                        },
                        "url": "https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2021-03-01",
                    }
                ]
            }

            # Get access token and make request
            token = await self._get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://management.azure.com/batch?api-version=2020-06-01",
                    headers=headers,
                    json=batch_payload,
                )
                response.raise_for_status()

                batch_result = response.json()

                # Extract the eviction rate data from batch response
                if not batch_result.get("responses"):
                    logger.warning("No responses in batch result")
                    return {}

                query_response = batch_result["responses"][0]
                if query_response.get("httpStatusCode") != 200:
                    logger.error(
                        f"Query failed with status {query_response.get('httpStatusCode')}"
                    )
                    return {}

                content = query_response.get("content", {})
                data = content.get("data", {})
                rows = data.get("rows", [])

                # Parse the table data into our result format
                # With the projected query, we get 3 columns: skuName, location, spotEvictionRate
                eviction_data = {}
                for row in rows:
                    try:
                        if (
                            len(row) >= 3
                        ):  # We expect exactly 3 columns from the projected query
                            sku_name = row[0]  # skuName column
                            location = row[1]  # location column
                            eviction_rate = row[2]  # spotEvictionRate column

                            if sku_name and location and eviction_rate:
                                if sku_name not in eviction_data:
                                    eviction_data[sku_name] = {}
                                eviction_data[sku_name][location] = eviction_rate
                    except Exception as e:
                        logger.warning(f"Error parsing eviction rate row: {e}")
                        continue

                logger.info(f"Retrieved eviction rates for {len(eviction_data)} SKUs")
                return eviction_data

        except Exception as e:
            logger.error(f"Failed to fetch eviction rates: {e}")
            return {}

    async def get_eviction_rate(self, sku_name: str, location: str) -> Optional[str]:
        """
        Get eviction rate for a specific SKU and location.

        Args:
            sku_name: The SKU name (e.g., 'standard_d2s_v4')
            location: The Azure region (e.g., 'eastus')

        Returns:
            Eviction rate string (e.g., '0-5', '5-10', '20+') or None if not found
        """
        eviction_data = await self.get_eviction_rates([sku_name], [location])
        return eviction_data.get(sku_name, {}).get(location)
