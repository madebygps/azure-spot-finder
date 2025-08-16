from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SKUItem(BaseModel):
    vmSku: str
    vCPUs: Optional[int] = None
    memoryGB: Optional[float] = None
    gpu: Optional[bool] = False
    supportsSpot: Optional[bool] = False
    zones: Optional[List[str]] = None
    vmSeries: Optional[str] = None

    class Config:
        # Accept and pass through any additional provider fields
        extra = "allow"


class SpotSKUsResponse(BaseModel):
    region: str
    timestamp: str
    total: int
    returned: int
    items: List[SKUItem]


class RawResponse(BaseModel):
    region: str
    timestamp: str
    items: List[Dict[str, Any]]


class SpotQueryParams(BaseModel):
    region: str
    raw: bool = False
    limit: int = 200
    offset: int = 0
    min_vcpus: Optional[int] = None
    max_vcpus: Optional[int] = None
    min_memory_gb: Optional[float] = None
    max_memory_gb: Optional[float] = None
    gpu: bool = False
    supports_spot: bool = True
    sku_like: Optional[str] = None
    series: Optional[str] = None
    zones: Optional[str] = None
    zones_match: str = "any"
    sort_by: str = "vmSku"
    sort_order: str = "asc"
    fields: Optional[str] = None
