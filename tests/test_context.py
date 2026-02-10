"""Tests for penstock._context."""

from __future__ import annotations

import asyncio

import pytest

from penstock._context import (
    FlowContext,
    _get_or_create_context,
    _reset_context,
    _set_context,
    current_flow_id,
    get_flow_context,
    get_flow_context_value,
    set_flow_context_value,
)


class TestFlowContext:
    def test_default_correlation_id(self) -> None:
        ctx = FlowContext()
        assert isinstance(ctx.correlation_id, str)
        assert len(ctx.correlation_id) == 32  # uuid4 hex

    def test_custom_correlation_id(self) -> None:
        ctx = FlowContext(correlation_id="abc")
        assert ctx.correlation_id == "abc"

    def test_get_set_delete(self) -> None:
        ctx = FlowContext()
        assert ctx.get_value("k") is None
        assert ctx.get_value("k", "fallback") == "fallback"

        ctx.set_value("k", 42)
        assert ctx.get_value("k") == 42

        ctx.delete_value("k")
        with pytest.raises(KeyError):
            ctx.delete_value("k")

    def test_metadata_snapshot(self) -> None:
        ctx = FlowContext()
        ctx.set_value("a", 1)
        snap = ctx.metadata
        snap["a"] = 999
        assert ctx.get_value("a") == 1  # original unchanged

    def test_fork_shares_correlation_id(self) -> None:
        parent = FlowContext(correlation_id="shared")
        child = parent.fork()
        assert child.correlation_id == "shared"

    def test_fork_deep_copies_metadata(self) -> None:
        parent = FlowContext()
        parent.set_value("nested", {"x": [1, 2]})
        child = parent.fork()

        child.set_value("nested", {"x": [1, 2, 3]})
        assert parent.get_value("nested") == {"x": [1, 2]}

    def test_fork_isolation(self) -> None:
        parent = FlowContext()
        parent.set_value("a", 1)
        child = parent.fork()
        child.set_value("b", 2)
        assert parent.get_value("b") is None


class TestContextVar:
    def test_no_context_returns_none(self) -> None:
        assert get_flow_context() is None
        assert current_flow_id() is None

    def test_get_or_create(self) -> None:
        ctx = _get_or_create_context()
        assert isinstance(ctx, FlowContext)
        # calling again returns the same instance
        assert _get_or_create_context() is ctx

    def test_set_and_reset(self) -> None:
        ctx = FlowContext(correlation_id="test")
        _set_context(ctx)
        assert current_flow_id() == "test"
        _reset_context()
        assert current_flow_id() is None


class TestPublicAPI:
    def test_set_and_get_value(self) -> None:
        set_flow_context_value("k", "v")
        assert get_flow_context_value("k") == "v"

    def test_get_value_no_context(self) -> None:
        assert get_flow_context_value("k") is None
        assert get_flow_context_value("k", "default") == "default"

    def test_set_creates_context(self) -> None:
        assert get_flow_context() is None
        set_flow_context_value("x", 1)
        assert get_flow_context() is not None
        assert current_flow_id() is not None


class TestAsyncPropagation:
    def test_context_inherited_by_task(self) -> None:
        async def run() -> None:
            _set_context(FlowContext(correlation_id="async-test"))
            set_flow_context_value("source", "parent")

            async def child() -> tuple[str | None, object]:
                return current_flow_id(), get_flow_context_value("source")

            cid, val = await asyncio.create_task(child())
            assert cid == "async-test"
            assert val == "parent"

        asyncio.run(run())
