from typing import Optional
from fastapi import Query

from backend.app.schemas import SpotQueryParams


def get_spot_query_params(
    region: str = Query(..., description="Azure region name, e.g. eastus"),
    raw: bool = Query(
        False, description="Return raw provider payload without server-side filtering"
    ),
    limit: int = Query(200, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for paging"),
    min_vcpus: Optional[int] = Query(None, ge=0),
    max_vcpus: Optional[int] = Query(None, ge=0),
    min_memory_gb: Optional[float] = Query(None, ge=0.0),
    max_memory_gb: Optional[float] = Query(None, ge=0.0),
    gpu: bool = Query(False, description="Include GPU SKUs (default false)"),
    supports_spot: bool = Query(True, description="Filter for supportsSpot values"),
    sku_like: Optional[str] = Query(None, description="Substring match for SKU name"),
    series: Optional[str] = Query(None, description="Comma separated vmSeries values"),
    zones: Optional[str] = Query(None, description="Comma separated zone ids to match"),
    zones_match: str = Query(
        "any", regex="^(any|all)$", description="Match any or all zones"
    ),
    sort_by: str = Query(
        "vmSku", description="Field to sort by (vmSku, vCPUs, memoryGB)"
    ),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    fields: Optional[str] = Query(
        None, description="Comma-separated fields to include in each item"
    ),
) -> SpotQueryParams:
    return SpotQueryParams(
        region=region,
        raw=raw,
        limit=limit,
        offset=offset,
        min_vcpus=min_vcpus,
        max_vcpus=max_vcpus,
        min_memory_gb=min_memory_gb,
        max_memory_gb=max_memory_gb,
        gpu=gpu,
        supports_spot=supports_spot,
        sku_like=sku_like,
        series=series,
        zones=zones,
        zones_match=zones_match,
        sort_by=sort_by,
        sort_order=sort_order,
        fields=fields,
    )
