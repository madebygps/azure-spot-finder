"""Dependency injection container and FastAPI dependencies."""

from typing import Optional
from fastapi import Request, HTTPException

from api.clients.compute_client import ComputeClient
from api.clients.pricing_client import PricingClient
from api.clients.eviction_client import EvictionClient
from api.clients.azure_client import AzureClient
from api.services.sku_service import SkuService


class DependencyContainer:
    """Container for managing application dependencies with proper lifecycle."""

    def __init__(self):
        self._azure_client: Optional[AzureClient] = None
        self._compute_client: Optional[ComputeClient] = None
        self._pricing_client: Optional[PricingClient] = None
        self._sku_service: Optional[SkuService] = None

    def create_azure_client(self) -> AzureClient:
        """Create or return cached Azure client instance (singleton pattern)."""
        if self._azure_client is None:
            self._azure_client = AzureClient()
        return self._azure_client

    def create_compute_client(self) -> ComputeClient:
        """Create or return cached compute client instance (singleton pattern)."""
        if self._compute_client is None:
            azure_client = self.create_azure_client()
            self._compute_client = ComputeClient(azure_client)
        return self._compute_client

    def create_pricing_client(self) -> PricingClient:
        """Create or return cached pricing client instance (singleton pattern)."""
        if self._pricing_client is None:
            self._pricing_client = PricingClient()
        return self._pricing_client

    def create_sku_service(self) -> SkuService:
        """Create or return cached SKU service instance (singleton pattern)."""
        if self._sku_service is None:
            azure_client = self.create_azure_client()
            eviction_client = EvictionClient(azure_client)
            self._sku_service = SkuService(
                client=self.create_compute_client(),
                pricing_client=self.create_pricing_client(),
                eviction_client=eviction_client,
            )
        return self._sku_service

    async def cleanup(self) -> None:
        """Clean up all managed dependencies."""
        if self._compute_client:
            await self._compute_client.close()
            self._compute_client = None
        if self._pricing_client:
            await self._pricing_client.close()
            self._pricing_client = None
        if self._azure_client:
            await self._azure_client.close()
            self._azure_client = None
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


def provide_azure_client(request: Request) -> AzureClient:
    """FastAPI dependency that provides the Azure client.

    Retrieves the Azure client from the application-scoped container.
    Raises HTTP 500 if the container is not properly initialized.
    """
    return _get_container(request).create_azure_client()


def provide_compute_client(request: Request) -> ComputeClient:
    """FastAPI dependency that provides the compute client.

    Retrieves the compute client from the application-scoped container.
    Raises HTTP 500 if the container is not properly initialized.
    """
    return _get_container(request).create_compute_client()


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
