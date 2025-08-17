import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.compute.aio import ComputeManagementClient

from .cache import get_cached, set_cached


load_dotenv()


class AzureSKUClient:
    """Minimal wrapper around Azure compute SKUs to list spot-capable SKUs for a region."""

    def __init__(self):
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not subscription_id:
            raise EnvironmentError(
                "AZURE_SUBSCRIPTION_ID environment variable is required."
                " Set AZURE_SUBSCRIPTION_ID to the target subscription id."
            )

        self.credential = DefaultAzureCredential()
        self.client = ComputeManagementClient(self.credential, subscription_id)

    async def list_spot_skus(self, region: str) -> List[Dict[str, Any]]:
        """Return a list of Spot capable SKU dicts for the given region."""
        region_lc = region.lower()
        cached = get_cached(region_lc)
        if cached is not None:
            return cached

        filter_expr = f"location eq '{region}'"
        results: List[Dict[str, Any]] = []

        async for sku in self.client.resource_skus.list(filter=filter_expr):
            resource_type_raw = getattr(sku, "resource_type", None) or ""
            resource_type = str(resource_type_raw).lower()

            if not ("virtualmachine" in resource_type or "compute" in resource_type):
                continue

            capabilities_list = list(getattr(sku, "capabilities", []) or [])
            caps = {
                (getattr(c, "name", "") or "").lower(): getattr(c, "value", None)
                for c in capabilities_list
            }
            low_priority = caps.get("lowprioritycapable")
            if not (low_priority is True or str(low_priority).lower() in ("true", "1")):
                continue

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
                continue

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

            name_lower = (str(getattr(sku, "name", "")) or "").lower()
            family_lower = (str(getattr(sku, "family", "")) or "").lower()
            # Exclude B-series VMs because Azure docs list B-series as
            # unsupported for Spot VMs. Some provider SKUs may include
            # LowPriorityCapable flags for B variants; explicitly filter
            if (
                name_lower.startswith("standard_b")
                or family_lower.startswith("standard_b")
                or family_lower.startswith("standardb")
            ):
                continue
            gpu_tokens = ("nc", "nd", "nv", "nsv2", "microsoft.hpcgpu", "gpu")
            has_gpu = any(tok in name_lower for tok in gpu_tokens) or any(
                tok in family_lower for tok in gpu_tokens
            )
            for c in capabilities_list:
                c_name = (getattr(c, "name", "") or "").lower()
                if "gpu" in c_name or "nvidia" in c_name:
                    has_gpu = True

            vcpus = _as_int(caps.get("vcpus"))
            memory_gb = _as_float(caps.get("memorygb"))

            zones_set = set()
            for li in getattr(sku, "location_info", []) or []:
                loc = (getattr(li, "location", None) or "").lower()
                if loc == region.lower() or not region:
                    for z in list(getattr(li, "zones", []) or []):
                        zones_set.add(str(z))

            minimal_restrictions = []
            for r in getattr(sku, "restrictions", []) or []:
                rc = getattr(r, "reason_code", None)
                rtype = getattr(r, "type", None)
                if rc or rtype:
                    minimal_restrictions.append({"type": rtype, "reason_code": rc})

            sku_dict: Dict[str, Any] = {
                "name": getattr(sku, "name", None),
                "size": getattr(sku, "size", None),
                "family": getattr(sku, "family", None),
                "has_gpu": has_gpu,
                "vcpus": vcpus,
                "memory_gb": memory_gb,
                "zones": sorted(list(zones_set)),
            }

            results.append(sku_dict)

        set_cached(region_lc, results)
        return results

    async def close(self) -> None:
        """Close underlying async client and credential transports."""
        try:
            await self.client.close()
        except Exception:
            pass
        try:
            await self.credential.close()
        except Exception:
            pass

    async def list_raw_skus(self, region: str):
        """Return the raw provider SKU objects for diagnostic inspection.

        This returns the upstream SDK objects (as-is) and should only be used
        for debugging; it does not cache or shape the data.
        """
        filter_expr = f"location eq '{region}'"
        items = []
        async for sku in self.client.resource_skus.list(filter=filter_expr):
            items.append(sku)
        return items
