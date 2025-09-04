from django.core.cache import cache


class CacheService:
    def get(self, namespace: str, key: str):
        """
        Retrieves data from the cache.

        Args:
            namespace: The namespace for the cache key.
            key: The key for the cache entry.

        Returns:
            The cached data, or None if it's not in the cache.
        """
        cache_key = f"{namespace}:{key}"
        return cache.get(cache_key)

    def set(self, namespace: str, key: str, value, timeout=None):
        """
        Sets data in the cache.

        Args:
            namespace: The namespace for the cache key.
            key: The key for the cache entry.
            value: The data to be cached.
            timeout: The cache timeout in seconds. If None, uses the default timeout.
        """
        cache_key = f"{namespace}:{key}"
        cache.set(cache_key, value, timeout)

    def delete(self, namespace: str, key: str):
        """
        Deletes data from the cache.

        Args:
            namespace: The namespace for the cache key.
            key: The key for the cache entry.
        """
        cache_key = f"{namespace}:{key}"
        cache.delete(cache_key)
