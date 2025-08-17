from typing import Optional
from fastapi import Request


def get_azure_client(request: Optional[Request] = None):
    """FastAPI dependency that returns the application AzureSKUClient."""
    if request is not None:
        client = getattr(request.app.state, "azure_client", None)
        if client is not None:
            return client

    # Lazy import to avoid circular import at module import time.
    from backend.app.main import get_client

    return get_client()
