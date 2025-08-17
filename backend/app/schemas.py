from pydantic import BaseModel
from typing import List, Optional


class Restriction(BaseModel):
    type: Optional[str]
    reason_code: Optional[str]


class SpotSku(BaseModel):
    name: Optional[str]
    size: Optional[str]
    family: Optional[str]
    has_gpu: Optional[bool]
    vcpus: Optional[int]
    memory_gb: Optional[float]
    zones: List[str] = []
    restrictions: List[Restriction] = []
