"""Tests for prompts module."""

from unittest.mock import Mock

import pytest

from talos_mcp.core.client import TalosClient
from talos_mcp.prompts import TalosPrompts


@pytest.fixture
def mock_client() -> Mock:
    """Create a mock TalosClient."""
    client = Mock(spec=TalosClient)
    return client


@pytest.fixture
def prompts(mock_client: Mock) -> TalosPrompts:
    """Create TalosPrompts instance with mocked client."""
    return TalosPrompts(mock_client)


class TestTalosPrompts:
    """Tests for TalosPrompts class."""

    async def test_list_prompts(self, prompts: TalosPrompts) -> None:
        """Test list_prompts returns expected prompts."""
        result = await prompts.list_prompts()
        assert len(result) == 2

        names = [p.name for p in result]
        assert "diagnose_cluster" in names
        assert "audit_review" in names

    async def test_list_prompts_has_arguments(self, prompts: TalosPrompts) -> None:
        """Test prompts have proper arguments defined."""
        result = await prompts.list_prompts()

        diagnose = next(p for p in result if p.name == "diagnose_cluster")
        assert len(diagnose.arguments) == 1
        assert diagnose.arguments[0].name == "node"
        assert diagnose.arguments[0].required is False

    async def test_get_prompt_diagnose_cluster(self, prompts: TalosPrompts) -> None:
        """Test get_prompt for diagnose_cluster."""
        result = await prompts.get_prompt("diagnose_cluster")
        assert len(result) == 1
        assert result[0].role == "user"
        assert "talos_health" in result[0].content.text

    async def test_get_prompt_diagnose_cluster_with_node(self, prompts: TalosPrompts) -> None:
        """Test get_prompt for diagnose_cluster with specific node."""
        result = await prompts.get_prompt("diagnose_cluster", {"node": "10.0.0.1"})
        assert "for node 10.0.0.1" in result[0].content.text

    async def test_get_prompt_audit_review(self, prompts: TalosPrompts) -> None:
        """Test get_prompt for audit_review."""
        result = await prompts.get_prompt("audit_review")
        assert len(result) == 1
        assert "talos_dashboard" in result[0].content.text
        assert "50 lines" in result[0].content.text

    async def test_get_prompt_audit_review_with_limit(self, prompts: TalosPrompts) -> None:
        """Test get_prompt for audit_review with custom limit."""
        result = await prompts.get_prompt("audit_review", {"limit": "100"})
        assert "100 lines" in result[0].content.text

    async def test_get_prompt_unknown_raises(self, prompts: TalosPrompts) -> None:
        """Test get_prompt raises for unknown prompt name."""
        with pytest.raises(ValueError, match="Unknown prompt"):
            await prompts.get_prompt("nonexistent_prompt")
