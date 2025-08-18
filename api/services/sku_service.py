from typing import List, Dict, Any, Optional

from api.clients.client import Client
from api.clients.pricing_client import PricingClient
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

    def __init__(self, client: Client, pricing_client: Optional[PricingClient] = None):
        self.client = client
        self.pricing_client = pricing_client

    async def list_spot_skus(
        self,
        region: str,
        include_gpu: bool = False,
        max_vcpus: Optional[int] = None,
        max_memory_gb: Optional[float] = None,
        include_pricing: bool = False,
        currency_code: str = "USD",
    ) -> List[Dict[str, Any]]:
        """List spot-capable VMs in the given region with optional resource filters.

        This method uses the Azure Management API to get all VM SKUs for a region,
        then filters and processes them to return only spot-capable instances.

        Args:
            region: Azure region name (e.g., 'eastus', 'westus2')
            include_gpu: GPU filtering behavior:
                - False (default): Return only non-GPU SKUs
                - True: Return only GPU-enabled SKUs
            max_vcpus: Maximum number of vCPUs to include (None = no limit)
            max_memory_gb: Maximum memory in GB to include (None = no limit)
            include_pricing: Whether to include pricing data (default: False)
            currency_code: Currency for pricing data (default: 'USD')

        Returns:
            List of spot-capable VM SKUs with their specifications and optional pricing
        """
        if not region or not region.strip():
            raise ValueError("Region parameter is required and cannot be empty")

        # Normalize region name
        region = region.strip().lower()

        # Check cache first
        cache_key = f"spot_skus:{region}:gpu={include_gpu}:vcpus={max_vcpus}:memory={max_memory_gb}:pricing={include_pricing}:currency={currency_code}"
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

                # Apply vCPU filtering
                vcpus = sku_specs.get("vcpus")
                if max_vcpus is not None and vcpus is not None and vcpus > max_vcpus:
                    continue

                # Apply memory filtering
                memory_gb = sku_specs.get("memory_gb")
                if (
                    max_memory_gb is not None
                    and memory_gb is not None
                    and memory_gb > max_memory_gb
                ):
                    continue

                processed_skus.append(sku_specs)

        # Sort for consistent ordering
        processed_skus = sorted(
            processed_skus, key=lambda x: (x.get("family", ""), x.get("name", ""))
        )

        # Add pricing data if requested
        if include_pricing and self.pricing_client and processed_skus:
            try:
                pricing_data = await self.pricing_client.get_pricing_for_skus(
                    sku_specs=processed_skus,
                    region=region,
                    currency_code=currency_code,
                )

                # Add pricing to each SKU
                for sku in processed_skus:
                    sku_name = sku.get("name")
                    if sku_name and sku_name in pricing_data and pricing_data[sku_name]:
                        # Flatten pricing - take the first (and only) pricing record
                        pricing_record = pricing_data[sku_name][0]
                        sku.update(
                            {
                                "price": pricing_record.get("price"),
                                "currency": pricing_record.get("currency"),
                                "location": pricing_record.get("location"),
                                "effective_start": pricing_record.get(
                                    "effective_start"
                                ),
                                "meter_name": pricing_record.get("meter_name"),
                                "product_name": pricing_record.get("product_name"),
                            }
                        )
                        # Add effective_end only if it exists
                        if pricing_record.get("effective_end"):
                            sku["effective_end"] = pricing_record.get("effective_end")

            except Exception as e:
                # Log pricing error but don't fail the entire request
                print(f"Failed to fetch pricing data: {e}")
                # No need to add empty pricing fields if pricing failed

        # Cache the results
        set_cached(cache_key, processed_skus)

        return processed_skus
