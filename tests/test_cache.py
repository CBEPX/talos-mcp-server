"""Tests for tool result caching."""

import asyncio
import pytest
from mcp.types import TextContent

from talos_mcp.core.cache import ToolCache, cached_tool, get_cache, invalidate_on_mutation
from talos_mcp.tools.base import CachedTool, MutatingTool
from talos_mcp.tools.system import GetVersionTool


class TestToolCache:
    """Test ToolCache functionality."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance."""
        return ToolCache()

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_for_missing_key(self, cache):
        """Test get returns None for non-existent key."""
        result = await cache.get("tool", {}, ttl_seconds=30)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """Test setting and getting cached value."""
        expected = [TextContent(type="text", text="test result")]
        
        await cache.set("tool", {}, expected)
        result = await cache.get("tool", {}, ttl_seconds=30)
        
        assert result == expected

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self, cache):
        """Test cached value expires after TTL."""
        await cache.set("tool", {}, "value")
        
        # Should be available immediately
        result = await cache.get("tool", {}, ttl_seconds=0.001)
        assert result == "value"
        
        # Wait for expiration
        await asyncio.sleep(0.01)
        
        # Should be expired now
        result = await cache.get("tool", {}, ttl_seconds=0.001)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_key_includes_arguments(self, cache):
        """Test that different arguments create different cache keys."""
        await cache.set("tool", {"arg": "1"}, "result1")
        await cache.set("tool", {"arg": "2"}, "result2")
        
        result1 = await cache.get("tool", {"arg": "1"}, ttl_seconds=30)
        result2 = await cache.get("tool", {"arg": "2"}, ttl_seconds=30)
        
        assert result1 == "result1"
        assert result2 == "result2"

    @pytest.mark.asyncio
    async def test_invalidate_removes_all_entries(self, cache):
        """Test invalidate clears all cache entries."""
        await cache.set("tool1", {}, "value1")
        await cache.set("tool2", {}, "value2")
        
        count = await cache.invalidate_all()
        
        assert count == 2
        assert await cache.get("tool1", {}, 30) is None
        assert await cache.get("tool2", {}, 30) is None

    @pytest.mark.asyncio
    async def test_invalidate_by_tool_name(self, cache):
        """Test invalidate can target specific tool."""
        await cache.set("tool1", {}, "value1")
        await cache.set("tool2", {}, "value2")
        
        count = await cache.invalidate("tool1")
        
        assert count == 1
        assert await cache.get("tool1", {}, 30) is None
        assert await cache.get("tool2", {}, 30) == "value2"

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Note: This is synchronous, cache is empty initially
        stats = cache.get_stats()
        
        assert "total_entries" in stats
        assert "tools" in stats


class TestCachedTool:
    """Test CachedTool functionality."""

    @pytest.mark.asyncio
    async def test_cached_tool_uses_cache(self, mock_talos_client):
        """Test that CachedTool uses cache for repeated calls."""
        from unittest.mock import AsyncMock
        
        tool = GetVersionTool(mock_talos_client)
        
        # Mock the client's execute_talosctl
        mock_execute = AsyncMock(return_value={
            "stdout": "Talos v1.12.0",
            "stderr": ""
        })
        mock_talos_client.execute_talosctl = mock_execute
        
        # First call should execute
        result1 = await tool.run({})
        
        # Second call should use cache
        result2 = await tool.run({})
        
        # Should only execute once
        assert mock_execute.call_count == 1
        assert "Talos v1.12.0" in result1[0].text
        assert result1[0].text == result2[0].text

    @pytest.mark.asyncio
    async def test_cached_tool_different_args_different_cache(self, mock_talos_client):
        """Test that different arguments use different cache entries."""
        from unittest.mock import AsyncMock
        
        tool = GetVersionTool(mock_talos_client)
        
        mock_execute = AsyncMock(return_value={
            "stdout": "Talos v1.12.0",
            "stderr": ""
        })
        mock_talos_client.execute_talosctl = mock_execute
        
        # Call with different arguments
        await tool.run({"nodes": "10.0.0.1"})
        await tool.run({"nodes": "10.0.0.2"})
        
        # Should execute twice (different cache keys)
        assert mock_execute.call_count == 2

    @pytest.mark.asyncio
    async def test_cached_tool_does_not_cache_errors(self, mock_talos_client):
        """Test that errors are not cached."""
        from unittest.mock import AsyncMock
        
        # Clear cache first
        cache = get_cache()
        await cache.invalidate_all()
        
        tool = GetVersionTool(mock_talos_client)
        
        # Simulate error by raising exception
        from talos_mcp.core.exceptions import TalosCommandError, ErrorCode
        error = TalosCommandError(
            ["talosctl", "version"], 1, "connection refused", ErrorCode.CONNECTION_FAILED
        )
        mock_execute = AsyncMock(side_effect=error)
        mock_talos_client.execute_talosctl = mock_execute
        
        # Call twice
        await tool.run({})
        await tool.run({})
        
        # Should execute twice (errors not cached)
        assert mock_execute.call_count == 2


class TestMutatingTool:
    """Test MutatingTool functionality."""

    @pytest.mark.asyncio
    async def test_mutating_tool_invalidates_cache(self, mock_talos_client):
        """Test that MutatingTool invalidates cache after execution."""
        from unittest.mock import AsyncMock
        
        # Set up cache with a value
        cache = get_cache()
        await cache.set("some_tool", {}, "cached_value")
        
        # Create a mutating tool
        class TestMutatingTool(MutatingTool):
            name = "test_mutate"
            description = "Test mutating tool"
            args_schema = type("Schema", (), {"model_json_schema": lambda: {}})()
            
            async def _run_impl(self, arguments):
                return [TextContent(type="text", text="mutated")]
        
        tool = TestMutatingTool(mock_talos_client)
        mock_talos_client.execute_talosctl = AsyncMock()
        
        # Execute mutating tool
        await tool.run({})
        
        # Cache should be invalidated
        assert await cache.get("some_tool", {}, 30) is None

    @pytest.mark.asyncio
    async def test_mutating_tool_has_is_mutation_flag(self, mock_talos_client):
        """Test that MutatingTool has is_mutation = True."""
        class TestMutatingTool(MutatingTool):
            name = "test_mutate"
            description = "Test mutating tool"
            args_schema = type("Schema", (), {"model_json_schema": lambda: {}})()
            
            async def _run_impl(self, arguments):
                return [TextContent(type="text", text="mutated")]
        
        tool = TestMutatingTool(mock_talos_client)
        
        assert tool.is_mutation is True


class TestCacheIntegration:
    """Test cache integration with real tools."""

    @pytest.mark.asyncio
    async def test_version_tool_caching(self, mock_talos_client):
        """Test that GetVersionTool properly caches results."""
        from unittest.mock import AsyncMock
        
        # Clear cache
        cache = get_cache()
        await cache.invalidate_all()
        
        tool = GetVersionTool(mock_talos_client)
        mock_talos_client.execute_talosctl = AsyncMock(return_value={
            "stdout": "Talos v1.12.0",
            "stderr": ""
        })
        
        # Call twice
        result1 = await tool.run({})
        result2 = await tool.run({})
        
        # Should be cached
        assert mock_talos_client.execute_talosctl.call_count == 1
        assert result1[0].text == result2[0].text
