from typing import List, Any, Dict
from dotenv import load_dotenv

from azure.mgmt.compute.aio import ComputeManagementClient
from api.clients.azure_client import AzureClient


load_dotenv()


class ComputeClient:
    """Azure Compute Management client for SKU and VM operations."""

    def __init__(self, azure_client: AzureClient):
        """Initialize Compute client with Azure client.

        Args:
            azure_client: Centralized Azure client for authentication
        """
        self.azure_client = azure_client
        self.credential = azure_client.get_async_credential()
        self.client = ComputeManagementClient(
            self.credential, azure_client.subscription_id
        )

    async def get_sku_specs(
        self, region: str, sku_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get technical specifications for specific SKU names in a region.

        This method fetches detailed specs (vCPUs, memory, GPU, zones) for
        specific SKUs rather than all SKUs in a region, making it much more
        efficient when we already know which SKUs we need.

        Args:
            region: Azure region name (e.g., 'eastus', 'westus2')
            sku_names: List of specific SKU names to get specs for

        Returns:
            Dict mapping SKU name to its specifications:
            {
                'Standard_D2s_v3': {
                    'name': 'Standard_D2s_v3',
                    'size': 'D2s_v3',
                    'family': 'standardDSv3Family',
                    'has_gpu': False,
                    'vcpus': 2,
                    'memory_gb': 8.0,
                    'zones': ['1', '2', '3'],
                    'supports_spot': True
                }
            }
        """
        if not sku_names:
            return {}

        # Create filter that includes the region and any of the specified SKUs
        # Format: "location eq 'region' and (name eq 'sku1' or name eq 'sku2' or ...)"
        region_filter = f"location eq '{region}'"
        sku_filters = [f"name eq '{sku}'" for sku in sku_names]
        sku_filter = f"({' or '.join(sku_filters)})"
        filter_expr = f"{region_filter} and {sku_filter}"

        results = {}

        async for sku in self.client.resource_skus.list(filter=filter_expr):
            sku_specs = self._extract_sku_specs(sku, region)
            if sku_specs:
                results[sku_specs["name"]] = sku_specs

        return results

    def _extract_sku_specs(self, sku: Any, region: str) -> Dict[str, Any] | None:
        """Extract standardized specifications from a raw Azure SKU object."""
        # Filter 1: Only include virtual machine SKUs
        resource_type_raw = getattr(sku, "resource_type", None) or ""
        resource_type = str(resource_type_raw).lower()
        if not ("virtualmachine" in resource_type or "compute" in resource_type):
            return None

        # Filter 2: Only include spot-capable SKUs
        capabilities_list = list(getattr(sku, "capabilities", []) or [])
        caps = {
            (getattr(c, "name", "") or "").lower(): getattr(c, "value", None)
            for c in capabilities_list
        }
        low_priority = caps.get("lowprioritycapable")
        if not (low_priority is True or str(low_priority).lower() in ("true", "1")):
            return None

        # Filter 3: Exclude SKUs not available for subscription
        restricted = False
        for r in getattr(sku, "restrictions", []) or []:
            rc = getattr(r, "reason_code", None)
            if not rc:
                continue
            if str(rc).lower() == "notavailableforsubscription":
                locs = list(getattr(r, "locations", []) or [])
                if not locs or region.lower() in [str(x).lower() for x in locs]:
                    restricted = True
                    break
        if restricted:
            return None

        # Business Rule: Exclude B-series VMs (unsupported for Spot)
        name_lower = (str(getattr(sku, "name", "")) or "").lower()
        family_lower = (str(getattr(sku, "family", "")) or "").lower()
        if (
            name_lower.startswith("standard_b")
            or family_lower.startswith("standard_b")
            or family_lower.startswith("standardb")
        ):
            return None

        # Business Logic: GPU detection using Azure GPU patterns
        gpu_patterns = (
            "_nc",
            "_nd",
            "_nv",
            "_nsv2",  # Underscore prefix to match series names
            "standard_nc",
            "standard_nd",
            "standard_nv",
            "standard_nsv2",  # Full patterns
            "microsoft.hpcgpu",
            "gpu",
        )
        has_gpu = any(pattern in name_lower for pattern in gpu_patterns) or any(
            pattern in family_lower for pattern in gpu_patterns
        )
        for c in capabilities_list:
            c_name = (getattr(c, "name", "") or "").lower()
            if "gpu" in c_name or "nvidia" in c_name:
                has_gpu = True

        # Business Logic: Architecture detection using Azure naming patterns
        # ARM64 SKUs include "p" in the series name (Dpls, Dps, Eps, Dpds, Epds)
        # x64 SKUs use traditional naming (Ds, Es, Fs, etc.)
        arm64_patterns = (
            "pls",  # Dplsv5, Dplsv6 series
            "pds",  # Dpdsv5, Dpdsv6 series
            "ps_",  # Dpsv5, Dpsv6 series
            "pds_",  # Dpdsv5, Dpdsv6 series
            "pls_",  # Dplsv5, Dplsv6 series
            "eps",  # Epsv5, Epsv6 series
            "epds",  # Epdsv5, Epdsv6 series
        )
        is_arm64 = any(pattern in name_lower for pattern in arm64_patterns) or any(
            pattern in family_lower for pattern in arm64_patterns
        )
        architecture = "Arm64" if is_arm64 else "x64"

        # Data transformation: Parse Azure values
        def _as_int(val):
            try:
                return int(val)
            except Exception:
                return None

        def _as_float(val):
            try:
                return float(val)
            except Exception:
                return None

        vcpus = _as_int(caps.get("vcpus"))
        memory_gb = _as_float(caps.get("memorygb"))

        # Data transformation: Extract availability zones
        zones_set = set()
        for li in getattr(sku, "location_info", []) or []:
            loc = (getattr(li, "location", None) or "").lower()
            if loc == region.lower() or not region:
                for z in list(getattr(li, "zones", []) or []):
                    zones_set.add(str(z))

        # Return standardized format
        return {
            "name": getattr(sku, "name", None),
            "size": getattr(sku, "size", None),
            "family": getattr(sku, "family", None),
            "has_gpu": has_gpu,
            "architecture": architecture,
            "vcpus": vcpus,
            "memory_gb": memory_gb,
            "zones": sorted(list(zones_set)),
        }

    async def list_raw_skus(self, region: str) -> List[Any]:
        """Return raw Azure SKU objects for the given region.

        This method makes the Azure API call and returns the raw SDK objects
        without any filtering, parsing, or business logic applied.

        Args:
            region: Azure region name (e.g., 'eastus', 'westus2')

        Returns:
            List of raw Azure ResourceSku objects from the SDK
        """
        filter_expr = f"location eq '{region}'"
        results: List[Any] = []

        async for sku in self.client.resource_skus.list(filter=filter_expr):
            results.append(sku)

        return results

    async def close(self) -> None:
        """Close underlying async client.

        Note: Credential cleanup is handled by the Azure client
        during application shutdown, not by individual clients.
        """
        try:
            await self.client.close()
        except Exception:
            pass
