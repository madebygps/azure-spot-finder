from cachetools import TTLCache

# Default cache for SKU data (30 minutes)
_sku_cache = TTLCache(maxsize=128, ttl=30 * 60)

# Pricing cache with longer TTL (4 hours)
_pricing_cache = TTLCache(maxsize=256, ttl=4 * 60 * 60)


def get_cached(key: str):
    """Get from SKU cache."""
    return _sku_cache.get(key)


def set_cached(key: str, value):
    """Set in SKU cache."""
    _sku_cache[key] = value


def get_pricing_cached(key: str):
    """Get from pricing cache."""
    return _pricing_cache.get(key)


def set_pricing_cached(key: str, value):
    """Set in pricing cache."""
    _pricing_cache[key] = value
