import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from talos_mcp.core.client import TalosClient


@pytest.fixture(scope="session", autouse=True)
def no_implicit_event_loop() -> None:
    """Keep pytest-asyncio from restoring an unclosed implicit Python 3.12 loop."""
    asyncio.set_event_loop(None)


@pytest.fixture
def mock_talos_client():
    client = MagicMock(spec=TalosClient)
    client.execute_talosctl = AsyncMock()
    return client
