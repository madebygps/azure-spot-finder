from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from api.config.dependencies import provide_sku_service
from api.services.sku_service import SkuService

router = APIRouter(prefix="/v1")

SkuServiceDep = Annotated[SkuService, Depends(provide_sku_service)]


@router.get("/spot-skus")
async def get_spot_skus(
    region: str, sku_service: SkuServiceDep, gpu: bool = False
) -> dict:
    """Get spot-capable VM SKUs for a given region.

    Args:
        region: Region name (e.g., 'eastus', 'westus2')
        gpu: Include GPU-enabled SKUs (default: False)
    """
    if not region:
        raise HTTPException(
            status_code=400, detail="region query parameter is required"
        )

    try:
        items = await sku_service.list_spot_skus(region, include_gpu=gpu)
        return {
            "items": items,
            "metadata": {"region": region, "include_gpu": gpu, "count": len(items)},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to query: " + str(e))
