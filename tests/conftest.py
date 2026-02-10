"""Shared fixtures that reset global state between tests."""

from __future__ import annotations

import pytest

from penstock._config import reset as reset_config
from penstock._context import _reset_context
from penstock._registry import _registry


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    """Reset the global registry, flow context, and config before every test."""
    _registry.clear()
    _reset_context()
    reset_config()
