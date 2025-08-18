"""Azure Retail Pricing API client.

This client handles interactions with the Azure Retail Prices API to get
real-time pricing information for Azure services, particularly for Spot VMs.
"""

import asyncio
from typing import List, Dict, Any, Optional
import httpx


class PricingClient:
    """Client for Azure Retail Prices API.

    This client handles:
    - Authentication-free access to public pricing API
    - Efficient filtering to minimize data transfer
    - Pagination handling for large result sets
    - Error handling and retries
    """

    BASE_URL = "https://prices.azure.com/api/retail/prices"
    API_VERSION = "2023-01-01-preview"  # Latest version with savings plan support
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client instance."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.TIMEOUT_SECONDS),
                follow_redirects=True,
            )
        return self._client

    async def get_spot_pricing(
        self,
        sku_names: List[str],
        region: str,
        currency_code: str = "USD",
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get spot pricing for specific SKUs in a region.

        This method efficiently queries the Azure Retail Prices API using
        multiple filters to minimize the amount of data returned.

        Args:
            sku_names: List of Azure SKU names (e.g., ['Standard_D2s_v3'])
            region: Azure region name (e.g., 'eastus')
            currency_code: Currency for pricing (default: 'USD')
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of pricing records matching the criteria
        """
        if not sku_names:
            return []

        # Process SKUs in smaller batches to avoid URL length limits
        batch_size = 10  # Process 10 SKUs at a time
        all_results = []

        for i in range(0, len(sku_names), batch_size):
            batch_skus = sku_names[i : i + batch_size]
            batch_results = await self._get_pricing_batch(
                batch_skus, region, currency_code
            )
            all_results.extend(batch_results)

            # Check if we've hit the max results limit
            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break

        return all_results

    async def _get_pricing_batch(
        self,
        sku_names: List[str],
        region: str,
        currency_code: str = "USD",
    ) -> List[Dict[str, Any]]:
        """Get pricing for a batch of SKUs."""
        # Build OData filter for efficient querying
        # Filter for: VM service + consumption pricing + specific region + specific SKUs
        filters = [
            "serviceName eq 'Virtual Machines'",
            "priceType eq 'Consumption'",  # Regular consumption pricing
            f"armRegionName eq '{region}'",
        ]

        # Add both Spot and Low Priority naming conventions
        spot_filter = (
            "(contains(meterName, 'Spot') or contains(meterName, 'Low Priority'))"
        )
        filters.append(spot_filter)

        # Add SKU filter - use OR conditions for multiple SKUs
        if len(sku_names) == 1:
            filters.append(f"armSkuName eq '{sku_names[0]}'")
        else:
            sku_filters = [f"armSkuName eq '{sku}'" for sku in sku_names]
            filters.append(f"({' or '.join(sku_filters)})")

        filter_expression = " and ".join(filters)

        # Build query parameters
        params = {
            "api-version": self.API_VERSION,
            "currencyCode": currency_code,
        }

        # Add the filter as a separate parameter to avoid double encoding
        params["$filter"] = filter_expression

        results = []
        next_url = None
        page_count = 0
        max_pages = 5  # Limit pages per batch

        try:
            while page_count < max_pages:
                if next_url:
                    # Use the next page URL directly (already contains all params)
                    response = await self._make_request("GET", next_url)
                else:
                    # First request with base URL and params
                    response = await self._make_request(
                        "GET", self.BASE_URL, params=params
                    )

                data = response.json()

                # Add items from this page
                page_items = data.get("Items", [])
                results.extend(page_items)

                # Get next page URL
                next_url = data.get("NextPageLink")
                if not next_url:
                    break

                page_count += 1

        except Exception as e:
            # Log error but don't fail completely - return partial results
            print(f"Error fetching pricing data for batch: {e}")
            if not results:
                raise

        return results

    async def get_pricing_for_skus(
        self,
        sku_specs: List[Dict[str, Any]],
        region: str,
        currency_code: str = "USD",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get pricing data for a list of SKU specifications.

        This is a convenience method that extracts SKU names from specs
        and returns pricing data keyed by SKU name.

        Args:
            sku_specs: List of SKU specifications (from SkuService)
            region: Azure region name
            currency_code: Currency for pricing

        Returns:
            Dict mapping SKU name to list of pricing records:
            {
                'Standard_D2s_v3': [
                    {
                        'armSkuName': 'Standard_D2s_v3',
                        'retailPrice': 0.096,
                        'meterName': 'D2s v3 Spot',
                        'currencyCode': 'USD',
                        ...
                    }
                ]
            }
        """
        # Extract unique SKU names
        sku_names = [spec["name"] for spec in sku_specs if spec.get("name") is not None]

        if not sku_names:
            return {}

        # Get pricing data
        pricing_records = await self.get_spot_pricing(
            sku_names=sku_names,
            region=region,
            currency_code=currency_code,
        )

        # Group by SKU name and filter to essential fields
        pricing_by_sku = {}
        for record in pricing_records:
            sku_name = record.get("armSkuName")
            meter_name = record.get("meterName", "")
            product_name = record.get("productName", "")

            # Filter for Linux + Spot pricing only
            is_spot_pricing = "Spot" in meter_name
            is_linux = "Windows" not in product_name

            if sku_name and is_spot_pricing and is_linux:
                if sku_name not in pricing_by_sku:
                    pricing_by_sku[sku_name] = []

                # Extract only the most relevant fields
                filtered_record = {
                    "price": record.get("retailPrice"),
                    "currency": record.get("currencyCode"),
                    "location": record.get("location"),
                    "effective_start": record.get("effectiveStartDate"),
                    "meter_name": record.get("meterName"),
                    "product_name": record.get("productName"),
                }

                # Only include effective_end if it exists (not all pricing has end dates)
                if record.get("effectiveEndDate"):
                    filtered_record["effective_end"] = record.get("effectiveEndDate")

                pricing_by_sku[sku_name].append(filtered_record)

        return pricing_by_sku

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        try:
            response = await self.client.request(method, url, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and retry_count < self.MAX_RETRIES:
                # Retry on server errors with exponential backoff
                wait_time = 2**retry_count
                await asyncio.sleep(wait_time)
                return await self._make_request(method, url, params, retry_count + 1)
            raise
        except (httpx.ConnectError, httpx.TimeoutException):
            if retry_count < self.MAX_RETRIES:
                # Retry on network errors
                wait_time = 2**retry_count
                await asyncio.sleep(wait_time)
                return await self._make_request(method, url, params, retry_count + 1)
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
