"""Dependency injection container and FastAPI dependencies."""

from typing import Optional
from fastapi import Request, HTTPException

from api.clients.client import Client
from api.clients.pricing_client import PricingClient
from api.services.sku_service import SkuService


class DependencyContainer:
    """Container for managing application dependencies with proper lifecycle."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._pricing_client: Optional[PricingClient] = None
        self._sku_service: Optional[SkuService] = None

    def create_client(self) -> Client:
        """Create or return cached client instance (singleton pattern)."""
        if self._client is None:
            self._client = Client()
        return self._client

    def create_pricing_client(self) -> PricingClient:
        """Create or return cached pricing client instance (singleton pattern)."""
        if self._pricing_client is None:
            self._pricing_client = PricingClient()
        return self._pricing_client

    def create_sku_service(self) -> SkuService:
        """Create or return cached SKU service instance (singleton pattern)."""
        if self._sku_service is None:
            client = self.create_client()
            pricing_client = self.create_pricing_client()
            self._sku_service = SkuService(client, pricing_client)
        return self._sku_service

    async def cleanup(self) -> None:
        """Clean up all managed dependencies."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pricing_client:
            await self._pricing_client.close()
            self._pricing_client = None
        self._sku_service = None


def _get_container(request: Request) -> DependencyContainer:
    """Helper to get container with proper error handling."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise HTTPException(
            status_code=500,
            detail="Application dependency container not initialized. "
            "Check that the ASGI lifespan is properly configured.",
        )
    return container


def provide_client(request: Request) -> Client:
    """FastAPI dependency that provides the client.

    Retrieves the client from the application-scoped container.
    Raises HTTP 500 if the container is not properly initialized.
    """
    return _get_container(request).create_client()


def provide_pricing_client(request: Request) -> PricingClient:
    """FastAPI dependency that provides the pricing client.

    Retrieves the pricing client from the application-scoped container.
    Raises HTTP 500 if the container is not properly initialized.
    """
    return _get_container(request).create_pricing_client()


def provide_sku_service(request: Request) -> SkuService:
    """FastAPI dependency that provides the SKU service.

    Retrieves the service from the application-scoped container.
    Raises HTTP 500 if the container is not properly initialized.
    """
    return _get_container(request).create_sku_service()
