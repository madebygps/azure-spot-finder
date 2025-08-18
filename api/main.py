from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.config.dependencies import DependencyContainer
from api.routes.sku_routes import router as sku_router
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ASGI lifespan context — creates and manages dependency container.

    Creates a dependency container for the application and ensures proper cleanup.
    """
    container = DependencyContainer()
    app.state.container = container

    try:
        yield
    finally:
        await container.cleanup()


app = FastAPI(title="spot-finder PoC", lifespan=lifespan, docs_url="/", redoc_url=None)

app.include_router(sku_router)

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
