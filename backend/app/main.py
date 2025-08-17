from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
import inspect

from backend.app.azure_client import AzureSKUClient
from backend.app.deps import get_azure_client
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ASGI lifespan context — creates a single AzureSKUClient for the app
    and attempts to close it on shutdown.
    """
    # startup: create client if not already present
    if getattr(app.state, "azure_client", None) is None:
        app.state.azure_client = AzureSKUClient()
    try:
        yield
    finally:
        # shutdown: attempt async cleanup if client exposes close
        client = getattr(app.state, "azure_client", None)
        if client is not None:
            close_fn = getattr(client, "close", None)
            if callable(close_fn):
                try:
                    # close may be async; await if it's a coroutine
                    res = close_fn()
                    if inspect.isawaitable(res):
                        await res
                except Exception:
                    # don't raise during shutdown
                    pass


app = FastAPI(title="spot-finder PoC", lifespan=lifespan)

_client: AzureSKUClient | None = None


def get_client() -> AzureSKUClient:
    """Return the application-level AzureSKUClient when running under FastAPI,
    or fall back to a module-level client for direct script execution.
    """
    client = getattr(app.state, "azure_client", None)
    if client is not None:
        return client

    global _client
    if _client is None:
        _client = AzureSKUClient()
    return _client


@app.get("/v1/spot-skus")
async def get_spot_skus(
    region: str, client: AzureSKUClient = Depends(get_azure_client)
):
    """Return spot-capable VM SKUs for a region with optional server-side filtering and shaping."""
    if not region:
        raise HTTPException(
            status_code=400, detail="region query parameter is required"
        )

    try:
        items = await client.list_spot_skus(region)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to query Azure: " + str(e))

    return items


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
