from unittest.mock import AsyncMock, MagicMock

import pytest

from talos_mcp.core.client import TalosClient


@pytest.fixture
def mock_talos_client():
    client = MagicMock(spec=TalosClient)
    client.execute_talosctl = AsyncMock()
    return client
