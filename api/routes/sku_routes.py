from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from api.config.dependencies import provide_sku_service
from api.services.sku_service import SkuService

router = APIRouter(prefix="/v1")

SkuServiceDep = Annotated[SkuService, Depends(provide_sku_service)]


@router.get("/spot-skus")
async def get_spot_skus(
    region: str,
    sku_service: SkuServiceDep,
    gpu: bool = False,
    max_vcpus: Optional[int] = Query(
        default=8, description="Maximum vCPUs (default: 8 for cost efficiency)"
    ),
    max_memory_gb: Optional[float] = Query(
        default=32.0,
        description="Maximum memory in GB (default: 32 for cost efficiency)",
    ),
    include_pricing: bool = Query(
        default=False,
        description="Include spot pricing data from Azure Retail Prices API",
    ),
    currency_code: str = Query(
        default="USD",
        description="Currency code for pricing (e.g., 'USD', 'EUR', 'GBP')",
    ),
) -> dict:
    """Get spot-capable VM SKUs for a given region with optional resource filters.

    Args:
        region: Region name (e.g., 'eastus', 'westus2')
        gpu: GPU filtering behavior:
            - False (default): Return only non-GPU SKUs
            - True: Return only GPU-enabled SKUs
        max_vcpus: Maximum number of vCPUs (default: 8)
        max_memory_gb: Maximum memory in GB (default: 32.0)
        include_pricing: Include real-time spot pricing data (default: False)
        currency_code: Currency for pricing data (default: 'USD')
    """
    if not region:
        raise HTTPException(
            status_code=400, detail="region query parameter is required"
        )

    try:
        items = await sku_service.list_spot_skus(
            region,
            include_gpu=gpu,
            max_vcpus=max_vcpus,
            max_memory_gb=max_memory_gb,
            include_pricing=include_pricing,
            currency_code=currency_code,
        )
        return {
            "items": items,
            "metadata": {
                "region": region,
                "include_gpu": gpu,
                "max_vcpus": max_vcpus,
                "max_memory_gb": max_memory_gb,
                "include_pricing": include_pricing,
                "currency_code": currency_code,
                "count": len(items),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to query: " + str(e))
