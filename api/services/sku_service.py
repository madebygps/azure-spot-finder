from typing import List, Dict, Any

from api.clients.client import Client
from api.utils.cache import get_cached, set_cached


class SkuService:
    """Service for Azure spot VM operations.

    This service handles:
    - Business logic and filtering rules
    - Spot VM detection and validation
    - GPU detection patterns
    - Data transformation and standardization
    - Caching strategy
    - Input validation and normalization

    The Client handles only raw Azure API interactions.
    """

    def __init__(self, client: Client):
        self.client = client

    async def list_spot_skus(
        self, region: str, include_gpu: bool = False
    ) -> List[Dict[str, Any]]:
        """List spot-capable VMs in the given region.

        This method uses the Azure Management API to get all VM SKUs for a region,
        then filters and processes them to return only spot-capable instances.

        Args:
            region: Azure region name (e.g., 'eastus', 'westus2')
            include_gpu: GPU filtering behavior:
                - False (default): Return only non-GPU SKUs
                - True: Return only GPU-enabled SKUs

        Returns:
            List of spot-capable VM SKUs with their specifications
        """
        if not region or not region.strip():
            raise ValueError("Region parameter is required and cannot be empty")

        # Normalize region name
        region = region.strip().lower()

        # Check cache first
        cache_key = f"spot_skus:{region}:gpu={include_gpu}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        # Get raw SKUs from Azure
        try:
            raw_skus = await self.client.list_raw_skus(region)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch SKUs from Azure: {e}")

        # Process and filter SKUs
        processed_skus = []
        for sku in raw_skus:
            sku_specs = self.client._extract_sku_specs(sku, region)
            if sku_specs:
                # Apply GPU filtering
                has_gpu = sku_specs.get("has_gpu", False)
                if include_gpu and not has_gpu:
                    # Skip non-GPU SKUs when GPU is specifically requested
                    continue
                elif not include_gpu and has_gpu:
                    # Skip GPU SKUs when GPU is not requested (default behavior)
                    continue
                processed_skus.append(sku_specs)

        # Sort for consistent ordering
        processed_skus = sorted(
            processed_skus, key=lambda x: (x.get("family", ""), x.get("name", ""))
        )

        # Cache the results
        set_cached(cache_key, processed_skus)

        return processed_skus
