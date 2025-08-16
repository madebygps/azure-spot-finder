import os
from typing import List, Dict

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.subscription import SubscriptionClient

from .cache import get_cached, set_cached


class AzureSKUClient:
    """Minimal wrapper around Azure compute SKUs to list spot-capable SKUs for a region."""

    def __init__(self):
        # Try environment first for explicit subscription choice
        subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
        self.credential = DefaultAzureCredential()

        if not subscription_id:
            # Attempt to discover a subscription id using the provided credentials.
            # This requires the credential to have permission to list subscriptions.
            try:
                sub_client = SubscriptionClient(self.credential)
                subs = list(sub_client.subscriptions.list())
            except Exception as exc:  # pragma: no cover - best-effort discovery
                raise EnvironmentError(
                    "AZURE_SUBSCRIPTION_ID not set and subscription discovery failed: "
                    + str(exc)
                    + ". Set AZURE_SUBSCRIPTION_ID or ensure the credential can list subscriptions."
                )

            if not subs:
                raise EnvironmentError(
                    "No subscriptions found for the current credentials. Set AZURE_SUBSCRIPTION_ID to the target subscription id."
                )

            # If multiple subscriptions are found, pick the first but warn the user.
            if len(subs) > 1:
                # Prefer any subscription that is in 'Enabled' state
                enabled = [
                    s
                    for s in subs
                    if (getattr(s, "state", "") or "").lower() == "enabled"
                ]
                chosen = enabled[0] if enabled else subs[0]
            else:
                chosen = subs[0]

            subscription_id = getattr(chosen, "subscription_id", None)

        if not subscription_id:
            raise EnvironmentError(
                "AZURE_SUBSCRIPTION_ID resolved to empty — set it explicitly to be safe"
            )

        self.client = ComputeManagementClient(self.credential, subscription_id)

    def _sku_supports_spot(self, sku) -> bool:
        # capabilities is a list of objects with name/value
        caps = getattr(sku, "capabilities", []) or []
        for c in caps:
            try:
                name = (c.name or "").lower()
                value = (c.value or "").lower()
            except Exception:
                continue
            if "lowpriority" in name or "spot" in name:
                if value == "true" or value == "yes" or value == "1":
                    return True
            # legacy flag name
            if name == "lowprioritycapable" and value == "true":
                return True
        # some SKUs may include resourceType or restrictions; conservatively return False
        return False

    def list_spot_skus(self, region: str) -> List[Dict]:
        """Return a list of sku dicts for the given region.

        Uses a short in-process cache to avoid repeated ARM calls.
        """
        region_lc = region.lower()
        cached = get_cached(region_lc)
        if cached is not None:
            return cached

        items: List[Dict] = []
        for sku in self.client.resource_skus.list():
            # sku.locations is list of regions where sku is available
            locations = [loc.lower() for loc in (getattr(sku, "locations", []) or [])]
            if region_lc not in locations:
                # check location_info which may have more granular zone info
                loc_info = getattr(sku, "location_info", []) or []
                found = False
                for li in loc_info:
                    if getattr(li, "location", "").lower() == region_lc:
                        found = True
                        break
                if not found:
                    continue

            if not self._sku_supports_spot(sku):
                continue

            # parse basic capabilities
            caps = {
                (c.name or ""): (c.value or "")
                for c in (getattr(sku, "capabilities", []) or [])
            }
            try:
                vcpus = int(caps.get("vCPUs") or caps.get("vCPUS") or 0)
            except Exception:
                try:
                    vcpus = int(caps.get("vcpu") or 0)
                except Exception:
                    vcpus = 0
            try:
                memory = float(caps.get("MemoryGB") or 0)
            except Exception:
                memory = 0.0

            zones = []
            for li in getattr(sku, "location_info", []) or []:
                if getattr(li, "location", "").lower() == region_lc:
                    zones = getattr(li, "zones", []) or []
                    break

            items.append(
                {
                    "vmSku": getattr(sku, "name", None),
                    "vmSeries": getattr(sku, "resource_type", None),
                    "vCPUs": vcpus,
                    "memoryGB": memory,
                    "gpu": "gpu" in (getattr(sku, "name", "") or "").lower(),
                    "supportsSpot": True,
                    "evictionPolicy": None,
                    "zones": zones,
                }
            )

        set_cached(region_lc, items)
        return items
