from cachetools import TTLCache

# simple in-process cache: max 128 entries, 30 minute TTL
_cache = TTLCache(maxsize=128, ttl=30 * 60)


def get_cached(region: str):
    return _cache.get(region)


def set_cached(region: str, value):
    _cache[region] = value
