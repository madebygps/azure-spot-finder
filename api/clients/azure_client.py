"""Centralized Azure client for managing authentication and core Azure services."""

import os
import time
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential


class AzureClient:
    """Centralized Azure client for authentication and core Azure services."""

    def __init__(self):
        self._sync_credential: Optional[DefaultAzureCredential] = None
        self._async_credential: Optional[AsyncDefaultAzureCredential] = None
        self._token_cache: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self._subscription_id: Optional[str] = None

        # Load subscription ID once during initialization
        self._subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not self._subscription_id:
            raise EnvironmentError(
                "AZURE_SUBSCRIPTION_ID environment variable is required. "
                "Set AZURE_SUBSCRIPTION_ID to the target subscription ID."
            )

    @property
    def subscription_id(self) -> str:
        """Get the Azure subscription ID."""
        if self._subscription_id is None:
            raise EnvironmentError(
                "AZURE_SUBSCRIPTION_ID environment variable is required. "
                "Set AZURE_SUBSCRIPTION_ID to the target subscription ID."
            )
        return self._subscription_id

    def get_sync_credential(self) -> DefaultAzureCredential:
        """Get a synchronous DefaultAzureCredential instance.

        This credential is suitable for sync operations like the EvictionClient
        that uses httpx synchronously or needs to make blocking auth calls.

        Returns:
            DefaultAzureCredential: Thread-safe sync credential instance
        """
        if self._sync_credential is None:
            self._sync_credential = DefaultAzureCredential()
        return self._sync_credential

    def get_async_credential(self) -> AsyncDefaultAzureCredential:
        """Get an asynchronous DefaultAzureCredential instance.

        This credential is suitable for async operations like the AzureClient
        that uses async Azure management client libraries.

        Returns:
            AsyncDefaultAzureCredential: Async-compatible credential instance
        """
        if self._async_credential is None:
            self._async_credential = AsyncDefaultAzureCredential()
        return self._async_credential

    async def get_management_token(self, force_refresh: bool = False) -> str:
        """Get an access token for Azure Management API with caching.

        This method implements token caching to avoid excessive authentication
        requests. Tokens are cached until 5 minutes before expiration.

        Args:
            force_refresh: If True, bypass cache and get a fresh token

        Returns:
            str: Valid access token for https://management.azure.com/
        """
        current_time = time.time()

        # Check if we have a valid cached token (with 5-minute buffer)
        if (
            not force_refresh
            and self._token_cache
            and self._token_expires_at
            and current_time < self._token_expires_at - 300
        ):
            return self._token_cache

        # Get fresh token using sync credential
        credential = self.get_sync_credential()
        token = credential.get_token("https://management.azure.com/.default")

        # Cache the token
        self._token_cache = token.token
        self._token_expires_at = float(token.expires_on)

        return token.token

    async def close(self) -> None:
        """Clean up credential resources.

        This method should be called during application shutdown to properly
        close any underlying connections or resources used by the credentials.
        """
        if self._async_credential:
            try:
                await self._async_credential.close()
            except Exception:
                pass  # Ignore cleanup errors
            self._async_credential = None

        if self._sync_credential:
            try:
                # Sync credentials don't typically have close methods,
                # but we clear the reference for garbage collection
                pass
            except Exception:
                pass
            self._sync_credential = None

        # Clear token cache
        self._token_cache = None
        self._token_expires_at = None
