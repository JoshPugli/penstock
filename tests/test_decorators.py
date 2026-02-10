"""Tests for penstock._decorators."""

from __future__ import annotations

import asyncio

import pytest

from penstock._context import current_flow_id, get_flow_context
from penstock._decorators import (
    _normalize_after,
    entrypoint,
    step,
)
from penstock._registry import _registry

# ---------------------------------------------------------------------------
# @entrypoint
# ---------------------------------------------------------------------------


class TestEntrypoint:
    def test_registration(self) -> None:
        @entrypoint("reg_flow")
        def start() -> None:
            pass

        info = _registry.get_flow("reg_flow")
        assert "start" in info.steps
        assert info.steps["start"].is_entrypoint is True

    def test_creates_flow_context(self) -> None:
        @entrypoint("ep_flow")
        def run() -> str | None:
            return current_flow_id()

        cid = run()
        assert isinstance(cid, str)
        assert len(cid) == 32

    def test_resets_context_after(self) -> None:
        @entrypoint("ep_flow2")
        def run() -> None:
            pass

        run()
        assert get_flow_context() is None

    def test_resets_context_on_exception(self) -> None:
        @entrypoint("ep_flow3")
        def run() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            run()
        assert get_flow_context() is None

    def test_with_custom_name(self) -> None:
        @entrypoint("f", name="custom_start")
        def run() -> None:
            pass

        info = _registry.get_flow("f")
        assert "custom_start" in info.steps

    def test_with_after(self) -> None:
        @entrypoint("f", after="previous")
        def run() -> None:
            pass

        info = _registry.get_flow("f")
        assert info.steps["run"].after == ("previous",)


# ---------------------------------------------------------------------------
# @step
# ---------------------------------------------------------------------------


class TestStep:
    def test_registration(self) -> None:
        @entrypoint("step_flow")
        def start() -> None:
            pass

        @step("step_flow", after="start")
        def process() -> None:
            pass

        info = _registry.get_flow("step_flow")
        assert "start" in info.steps
        assert "process" in info.steps
        assert info.steps["process"].is_entrypoint is False
        assert info.steps["process"].after == ("start",)

    def test_reuses_context(self) -> None:
        @step("step_flow2", after="start")
        def process() -> None:
            assert current_flow_id() is not None

        @entrypoint("step_flow2")
        def start() -> str | None:
            cid = current_flow_id()
            process()
            return cid

        cid = start()
        assert cid is not None

    def test_step_outside_context_raises(self) -> None:
        @step("step_flow3", after="start")
        def process() -> None:
            pass

        with pytest.raises(RuntimeError, match="outside of a flow context"):
            process()

    def test_step_with_after_string(self) -> None:
        @step("f", after="validate")
        def process() -> None:
            pass

        info = _registry.get_flow("f")
        assert info.steps["process"].after == ("validate",)

    def test_step_with_after_callable(self) -> None:
        @entrypoint("f2")
        def start() -> None:
            pass

        @step("f2", after=start)
        def process() -> None:
            pass

        info = _registry.get_flow("f2")
        assert info.steps["process"].after == ("start",)

    def test_step_with_after_list(self) -> None:
        @step("f3", after=["a", "b"])
        def process() -> None:
            pass

        info = _registry.get_flow("f3")
        assert info.steps["process"].after == ("a", "b")


# ---------------------------------------------------------------------------
# after= normalization
# ---------------------------------------------------------------------------


class TestNormalizeAfter:
    def test_none(self) -> None:
        assert _normalize_after(None) == ()

    def test_string(self) -> None:
        assert _normalize_after("validate") == ("validate",)

    def test_callable(self) -> None:
        def my_func() -> None:
            pass

        assert _normalize_after(my_func) == ("my_func",)

    def test_list_mixed(self) -> None:
        def my_func() -> None:
            pass

        result = _normalize_after(["validate", my_func])
        assert result == ("validate", "my_func")

    def test_list_strings(self) -> None:
        assert _normalize_after(["a", "b"]) == ("a", "b")


# ---------------------------------------------------------------------------
# Async support
# ---------------------------------------------------------------------------


class TestAsync:
    def test_async_entrypoint(self) -> None:
        @entrypoint("async_flow")
        async def start() -> str | None:
            return current_flow_id()

        cid = asyncio.run(start())
        assert isinstance(cid, str)
        assert len(cid) == 32
        # Context should be reset after
        assert get_flow_context() is None

    def test_async_step(self) -> None:
        @step("async_flow2", after="start")
        async def process() -> None:
            assert current_flow_id() is not None

        @entrypoint("async_flow2")
        async def start() -> str | None:
            cid = current_flow_id()
            await process()
            return cid

        cid = asyncio.run(start())
        assert cid is not None

    def test_async_step_outside_context_raises(self) -> None:
        @step("async_flow3", after="start")
        async def process() -> None:
            pass

        with pytest.raises(RuntimeError, match="outside of a flow context"):
            asyncio.run(process())


# ---------------------------------------------------------------------------
# Methods in a class (no @flow needed)
# ---------------------------------------------------------------------------


class TestMethodsInClass:
    def test_methods_register_and_run(self) -> None:
        class OrderFlow:
            @entrypoint("order")
            def receive(self, order_id: str) -> str | None:
                cid = current_flow_id()
                self.validate(order_id)
                return cid

            @step("order", after="receive")
            def validate(self, order_id: str) -> None:
                assert current_flow_id() is not None

        info = _registry.get_flow("order")
        assert "receive" in info.steps
        assert "validate" in info.steps

        cid = OrderFlow().receive("ORD-1")
        assert isinstance(cid, str)
        assert len(cid) == 32
