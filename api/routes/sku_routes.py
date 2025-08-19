from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from api.config.dependencies import provide_sku_service
from api.services.sku_service import SkuService
from api.services.recommendation_service import (
    RecommendationService,
    RecommendationCriteria,
)

router = APIRouter(prefix="/v1")

SkuServiceDep = Annotated[SkuService, Depends(provide_sku_service)]


@router.get("/spot-skus")
async def get_spot_skus(
    region: str,
    sku_service: SkuServiceDep,
    gpu: bool = False,
    architecture: Optional[str] = Query(
        default=None,
        description="Filter by CPU architecture: 'x64' for Intel/AMD, 'Arm64' for ARM processors",
    ),
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
    include_eviction_rates: bool = Query(
        default=False,
        description="Include eviction rate data from Azure Resource Graph",
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
        architecture: CPU architecture filter:
            - None (default): Return all architectures
            - 'x64': Return only Intel/AMD x64 SKUs
            - 'Arm64': Return only ARM64 SKUs (Ampere Altra, Azure Cobalt 100)
        max_vcpus: Maximum number of vCPUs (default: 8)
        max_memory_gb: Maximum memory in GB (default: 32.0)
        include_pricing: Include real-time spot pricing data (default: False)
        include_eviction_rates: Include eviction rate data (default: False)
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
            architecture=architecture,
            max_vcpus=max_vcpus,
            max_memory_gb=max_memory_gb,
            include_pricing=include_pricing,
            include_eviction_rates=include_eviction_rates,
            currency_code=currency_code,
        )
        return {
            "items": items,
            "metadata": {
                "region": region,
                "include_gpu": gpu,
                "architecture": architecture,
                "max_vcpus": max_vcpus,
                "max_memory_gb": max_memory_gb,
                "include_pricing": include_pricing,
                "include_eviction_rates": include_eviction_rates,
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


@router.get("/spot-recommendations")
async def get_spot_recommendations(
    region: str,
    sku_service: SkuServiceDep,
    limit: int = Query(
        default=5, description="Number of recommendations to return (max: 10)"
    ),
    optimize_for: str = Query(
        default="balanced",
        description="Optimization strategy: 'cost', 'reliability', 'performance', 'balanced'",
    ),
    max_hourly_cost: Optional[float] = Query(
        default=None, description="Maximum acceptable hourly cost"
    ),
    max_eviction_rate: Optional[str] = Query(
        default=None,
        description="Maximum eviction rate: '0-5', '5-10', '10-15', '15-20', '20+'",
    ),
    architecture_preference: Optional[str] = Query(
        default=None, description="Preferred architecture: 'x64' or 'Arm64'"
    ),
    gpu: bool = False,
    max_vcpus: Optional[int] = Query(
        default=8, description="Maximum vCPUs (default: 8 for cost efficiency)"
    ),
    max_memory_gb: Optional[float] = Query(
        default=32.0,
        description="Maximum memory in GB (default: 32 for cost efficiency)",
    ),
    currency_code: str = Query(
        default="USD",
        description="Currency code for pricing (e.g., 'USD', 'EUR', 'GBP')",
    ),
) -> dict:
    """Get intelligent spot instance recommendations based on multiple factors.

    This endpoint analyzes all available spot SKUs and returns the top recommendations
    based on a composite score considering price, eviction rates, performance,
    availability, and architecture preferences.

    Args:
        region: Region name (e.g., 'eastus', 'westus2')
        limit: Number of recommendations (1-10, default: 5)
        optimize_for: Optimization strategy - 'cost', 'reliability', 'performance', 'balanced'
        max_hourly_cost: Maximum acceptable hourly cost constraint
        max_eviction_rate: Maximum eviction rate constraint
        architecture_preference: Preferred CPU architecture
        gpu: Include GPU instances (default: false)
        max_vcpus: Maximum vCPUs (default: 8)
        max_memory_gb: Maximum memory in GB (default: 32.0)
        currency_code: Currency for pricing data (default: 'USD')
    """
    if not region:
        raise HTTPException(
            status_code=400, detail="region query parameter is required"
        )

    # Validate parameters
    if limit < 1 or limit > 10:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 10")

    if optimize_for not in ("cost", "reliability", "performance", "balanced"):
        raise HTTPException(
            status_code=400,
            detail="optimize_for must be one of: cost, reliability, performance, balanced",
        )

    if architecture_preference and architecture_preference not in ("x64", "Arm64"):
        raise HTTPException(
            status_code=400, detail="architecture_preference must be 'x64' or 'Arm64'"
        )

    if max_eviction_rate and max_eviction_rate not in (
        "0-5",
        "5-10",
        "10-15",
        "15-20",
        "20+",
    ):
        raise HTTPException(
            status_code=400,
            detail="max_eviction_rate must be one of: 0-5, 5-10, 10-15, 15-20, 20+",
        )

    try:
        # Get all spot SKUs with pricing and eviction data
        skus = await sku_service.list_spot_skus(
            region,
            include_gpu=gpu,
            max_vcpus=max_vcpus,
            max_memory_gb=max_memory_gb,
            include_pricing=True,  # Always include pricing for recommendations
            include_eviction_rates=True,  # Always include eviction rates
            currency_code=currency_code,
        )

        if not skus:
            return {
                "recommendations": [],
                "metadata": {
                    "region": region,
                    "criteria": {
                        "optimize_for": optimize_for,
                        "max_hourly_cost": max_hourly_cost,
                        "max_eviction_rate": max_eviction_rate,
                        "architecture_preference": architecture_preference,
                    },
                    "count": 0,
                    "message": "No spot SKUs found matching criteria",
                },
            }

        # Create recommendation criteria
        criteria = RecommendationCriteria(
            max_hourly_cost=max_hourly_cost,
            max_eviction_rate=max_eviction_rate,
            optimize_for=optimize_for,  # type: ignore
            architecture_preference=architecture_preference,
        )

        # Get recommendations
        recommendations = RecommendationService.recommend_top_skus(
            skus, criteria, limit
        )

        return {
            "recommendations": recommendations,
            "metadata": {
                "region": region,
                "criteria": {
                    "optimize_for": optimize_for,
                    "max_hourly_cost": max_hourly_cost,
                    "max_eviction_rate": max_eviction_rate,
                    "architecture_preference": architecture_preference,
                    "include_gpu": gpu,
                    "max_vcpus": max_vcpus,
                    "max_memory_gb": max_memory_gb,
                    "currency_code": currency_code,
                },
                "total_skus_analyzed": len(skus),
                "recommendations_returned": len(recommendations),
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to generate recommendations: " + str(e)
        )
