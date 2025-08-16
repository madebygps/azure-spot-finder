from typing import List, Dict, Optional, Tuple


DEFAULT_MIN_LIMIT = 1


def _matches_zones(
    item_zones: List[str], wanted: Optional[List[str]], match_mode: str
) -> bool:
    if not wanted:
        return True
    item_set = set(map(str, item_zones or []))
    wanted_set = set(map(str, wanted))
    if match_mode == "all":
        return wanted_set.issubset(item_set)
    return bool(item_set & wanted_set)


def _as_minimal(item: Dict, fields: Optional[List[str]] = None) -> Dict:
    # Default minimal fields
    default = ["vmSku", "vCPUs", "memoryGB", "gpu", "supportsSpot", "zones"]
    include = fields or default
    return {k: item.get(k) for k in include if k in item}


def filter_and_shape_items(
    items: List[Dict],
    min_vcpus: Optional[int] = None,
    max_vcpus: Optional[int] = None,
    min_memory_gb: Optional[float] = None,
    max_memory_gb: Optional[float] = None,
    gpu: bool = False,
    supports_spot: bool = True,
    sku_like: Optional[str] = None,
    series: Optional[str] = None,
    zones: Optional[str] = None,
    zones_match: str = "any",
    sort_by: str = "vmSku",
    sort_order: str = "asc",
    offset: int = 0,
    limit: int = 200,
    fields: Optional[str] = None,
) -> Tuple[List[Dict], int]:
    """Filter, dedupe and shape a list of sku items.

    Returns a tuple of (filtered_items, total_matching_before_limit)
    """
    # sanitize inputs
    wanted_zones = [z.strip() for z in zones.split(",")] if zones else None
    series_set = set([s.strip().lower() for s in series.split(",")]) if series else None
    sku_like_lc = sku_like.lower() if sku_like else None
    fields_list = [f.strip() for f in fields.split(",")] if fields else None

    # drop invalid items and ensure shape
    clean: List[Dict] = []
    for it in items:
        if not it or not isinstance(it, dict):
            continue
        sku = it.get("vmSku")
        if not sku:
            continue
        clean.append(it)

    # dedupe by vmSku, keep one and union zones
    dedup: Dict[str, Dict] = {}
    for it in clean:
        key = it.get("vmSku")
        # guard against None to satisfy static checkers (clean should have filtered these)
        if key is None:
            continue
        if key in dedup:
            existing = dedup[key]
            # union zones
            ez = set(existing.get("zones") or [])
            iz = set(it.get("zones") or [])
            existing["zones"] = sorted(ez | iz)
            # prefer non-zero vCPU and memory if present
            if not existing.get("vCPUs") and it.get("vCPUs"):
                existing["vCPUs"] = it.get("vCPUs")
            if not existing.get("memoryGB") and it.get("memoryGB"):
                existing["memoryGB"] = it.get("memoryGB")
        else:
            # normalize zones to strings
            it_copy = dict(it)
            it_copy["zones"] = [str(z) for z in (it_copy.get("zones") or [])]
            dedup[key] = it_copy

    pool = list(dedup.values())

    # filtering
    filtered: List[Dict] = []
    for it in pool:
        if supports_spot and not it.get("supportsSpot", False):
            continue
        if not gpu and it.get("gpu", False):
            continue
        v = it.get("vCPUs") or 0
        if min_vcpus is not None and v < min_vcpus:
            continue
        if max_vcpus is not None and v > max_vcpus:
            continue
        m = it.get("memoryGB") or 0.0
        if min_memory_gb is not None and m < min_memory_gb:
            continue
        if max_memory_gb is not None and m > max_memory_gb:
            continue
        if sku_like_lc and sku_like_lc not in (it.get("vmSku") or "").lower():
            continue
        if series_set and (it.get("vmSeries") or "").lower() not in series_set:
            continue
        if not _matches_zones(it.get("zones") or [], wanted_zones, zones_match):
            continue
        filtered.append(it)

    total_matching = len(filtered)

    # sorting
    reverse = sort_order == "desc"
    try:
        filtered.sort(
            key=lambda x: (x.get(sort_by) is None, x.get(sort_by)), reverse=reverse
        )
    except Exception:
        # fallback to vmSku sort
        filtered.sort(key=lambda x: x.get("vmSku") or "")

    # pagination
    offset = max(0, offset or 0)
    limit = max(DEFAULT_MIN_LIMIT, min(1000, limit or 200))
    page = filtered[offset : offset + limit]

    # shape fields
    result = []
    for it in page:
        if fields_list is None:
            result.append(_as_minimal(it, fields_list))
        else:
            result.append(_as_minimal(it, fields_list))

    return result, total_matching
