from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends

# Use absolute import so the module can be executed directly (python backend/app/main.py)
from backend.app.azure_client import AzureSKUClient
from backend.app.filters import filter_and_shape_items
from backend.app import schemas
from backend.app.params import get_spot_query_params

app = FastAPI(title="spot-finder PoC")

# create client lazily to surfice startup even if env isn't configured
_client: AzureSKUClient | None = None


def get_client() -> AzureSKUClient:
    global _client
    if _client is None:
        _client = AzureSKUClient()
    return _client


@app.get("/v1/spot-skus")
def get_spot_skus(params: schemas.SpotQueryParams = Depends(get_spot_query_params)):
    """Return spot-capable VM SKUs for a region with optional server-side filtering and shaping.

    Default behaviour: return spot-capable, non-GPU SKUs with minimal fields unless `raw=true`.
    """
    if not params.region:
        raise HTTPException(
            status_code=400, detail="region query parameter is required"
        )

    client = get_client()
    try:
        items = client.list_spot_skus(params.region)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to query Azure: " + str(e))

    # raw passthrough for debugging/inspection
    if params.raw:
        resp = schemas.RawResponse(
            region=params.region,
            timestamp=datetime.utcnow().isoformat() + "Z",
            items=items,
        )
        return resp

    # delegate filtering/shape logic
    filtered, total = filter_and_shape_items(
        items,
        min_vcpus=params.min_vcpus,
        max_vcpus=params.max_vcpus,
        min_memory_gb=params.min_memory_gb,
        max_memory_gb=params.max_memory_gb,
        gpu=params.gpu,
        supports_spot=params.supports_spot,
        sku_like=params.sku_like,
        series=params.series,
        zones=params.zones,
        zones_match=params.zones_match,
        sort_by=params.sort_by,
        sort_order=params.sort_order,
        offset=params.offset,
        limit=params.limit,
        fields=params.fields,
    )

    # validate and return with Pydantic models
    items_models = [schemas.SKUItem.model_validate(it) for it in filtered]
    resp = schemas.SpotSKUsResponse(
        region=params.region,
        timestamp=datetime.utcnow().isoformat() + "Z",
        total=total,
        returned=len(items_models),
        items=items_models,
    )
    return resp


if __name__ == "__main__":
    # Allow running the app directly for quick local development:
    # python backend/app/main.py
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
