"""Caching utilities for MCP tool results.

Provides TTL-based caching for read-only operations to reduce
unnecessary talosctl invocations.
"""

import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from loguru import logger

if TYPE_CHECKING:
    from mcp.types import TextContent

T = TypeVar("T")


class ToolCache:
    """TTL-based cache for tool results.

    This cache stores results of read-only tool executions with a time-to-live (TTL)
    to avoid repeated expensive operations like talosctl calls.

    The cache is automatically invalidated when mutating operations are detected.
    """

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Create a cache key from tool name and arguments.

        Args:
            tool_name: Name of the tool.
            arguments: Tool arguments.

        Returns:
            String cache key.
        """
        # Sort arguments for consistent key generation
        args_str = str(sorted(arguments.items())) if arguments else ""
        return f"{tool_name}:{args_str}"

    async def get(
        self, tool_name: str, arguments: dict[str, Any], ttl_seconds: float
    ) -> Any | None:
        """Get cached result if available and not expired.

        Args:
            tool_name: Name of the tool.
            arguments: Tool arguments.
            ttl_seconds: Time-to-live in seconds.

        Returns:
            Cached result or None if not found or expired.
        """
        async with self._lock:
            key = self._make_key(tool_name, arguments)
            if key not in self._cache:
                return None

            result, timestamp = self._cache[key]
            age = time.time() - timestamp

            if age > ttl_seconds:
                # Cache expired
                del self._cache[key]
                logger.debug(f"Cache expired for {tool_name}")
                return None

            logger.debug(f"Cache hit for {tool_name} (age: {age:.1f}s)")
            return result

    async def set(self, tool_name: str, arguments: dict[str, Any], result: Any) -> None:
        """Store result in cache.

        Args:
            tool_name: Name of the tool.
            arguments: Tool arguments.
            result: Result to cache.
        """
        async with self._lock:
            key = self._make_key(tool_name, arguments)
            self._cache[key] = (result, time.time())
            logger.debug(f"Cached result for {tool_name}")

    async def invalidate(self, tool_name: str | None = None) -> int:
        """Invalidate cache entries.

        Args:
            tool_name: If provided, invalidate only entries for this tool.
                      If None, invalidate all entries.

        Returns:
            Number of entries invalidated.
        """
        async with self._lock:
            if tool_name is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Invalidated all cache entries ({count} items)")
                return count
            else:
                keys_to_remove = [key for key in self._cache if key.startswith(f"{tool_name}:")]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.info(f"Invalidated {len(keys_to_remove)} cache entries for {tool_name}")
                return len(keys_to_remove)

    async def invalidate_all(self) -> int:
        """Invalidate all cache entries.

        Returns:
            Number of entries invalidated.
        """
        return await self.invalidate(None)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics.
        """
        total_entries = len(self._cache)

        # Count by tool
        tools: dict[str, int] = {}
        for key in self._cache:
            tool_name = key.split(":")[0]
            tools[tool_name] = tools.get(tool_name, 0) + 1

        return {
            "total_entries": total_entries,
            "tools": tools,
        }


# Global cache instance
_global_cache = ToolCache()


def get_cache() -> ToolCache:
    """Get the global cache instance.

    Returns:
        Global ToolCache instance.
    """
    return _global_cache


def cached_tool(ttl_seconds: float = 30) -> Callable:
    """Decorator to cache tool results.

    This decorator caches the results of read-only tool executions.
    The cache is keyed by tool name and arguments.

    Args:
        ttl_seconds: Time-to-live for cached results in seconds.
                    Default is 30 seconds.

    Example:
        @cached_tool(ttl_seconds=60)
        async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
            # This result will be cached for 60 seconds
            return await self.execute_talosctl(["version", "-n", nodes])
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self: Any, arguments: dict[str, Any]) -> Any:
            # Get cache instance
            cache = get_cache()
            tool_name = getattr(self, "name", "unknown")

            # Try to get from cache
            cached_result = await cache.get(tool_name, arguments, ttl_seconds)
            if cached_result is not None:
                logger.info(f"Using cached result for {tool_name}")
                return cached_result

            # Execute the tool
            result = await func(self, arguments)

            # Cache the result (only if successful - no errors in result)
            should_cache = True
            if isinstance(result, list) and result:
                if hasattr(result[0], "text"):
                    text = result[0].text
                    # Don't cache error results
                    if text.startswith("Error") or text.startswith("```\nError"):
                        should_cache = False
                        logger.debug(f"Not caching error result for {tool_name}")

            if should_cache:
                await cache.set(tool_name, arguments, result)

            return result

        # Attach cache info to the function for testing/monitoring
        wrapper._cache_ttl = ttl_seconds  # type: ignore
        wrapper._cache_enabled = True  # type: ignore

        return wrapper

    return decorator


def invalidate_on_mutation(func: Callable) -> Callable:
    """Decorator to invalidate cache after mutating operations.

    This decorator should be used on tools that modify state (is_mutation=True).
    It invalidates the entire cache after successful execution to ensure
    read-only tools return fresh data.

    Args:
        func: The function to decorate.

    Example:
        @invalidate_on_mutation
        async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
            # This will invalidate all caches after execution
            return await self.execute_talosctl(["reboot", "-n", nodes])
    """

    @wraps(func)
    async def wrapper(self: Any, arguments: dict[str, Any]) -> Any:
        result = await func(self, arguments)

        # Invalidate cache after mutation
        cache = get_cache()
        await cache.invalidate_all()
        logger.info("Cache invalidated after mutation")

        return result

    return wrapper
