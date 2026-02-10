"""Tests for penstock._types dataclasses."""

from __future__ import annotations

import pytest

from penstock._types import FlowInfo, StepInfo


class TestStepInfo:
    def test_creation(self) -> None:
        s = StepInfo(name="a", flow_name="f", after=(), is_entrypoint=False)
        assert s.name == "a"
        assert s.flow_name == "f"
        assert s.after == ()
        assert s.is_entrypoint is False

    def test_frozen(self) -> None:
        s = StepInfo(name="a", flow_name="f", after=(), is_entrypoint=False)
        with pytest.raises(AttributeError):
            s.name = "b"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = StepInfo(name="a", flow_name="f", after=("x",), is_entrypoint=True)
        b = StepInfo(name="a", flow_name="f", after=("x",), is_entrypoint=True)
        assert a == b

    def test_inequality(self) -> None:
        a = StepInfo(name="a", flow_name="f", after=(), is_entrypoint=True)
        b = StepInfo(name="a", flow_name="f", after=(), is_entrypoint=False)
        assert a != b


class TestFlowInfo:
    def test_creation(self) -> None:
        step = StepInfo(name="s", flow_name="f", after=(), is_entrypoint=True)
        flow = FlowInfo(name="f", steps={"s": step}, entrypoints=frozenset({"s"}))
        assert flow.name == "f"
        assert flow.steps["s"] is step
        assert "s" in flow.entrypoints

    def test_frozen(self) -> None:
        flow = FlowInfo(name="f", steps={}, entrypoints=frozenset())
        with pytest.raises(AttributeError):
            flow.name = "g"  # type: ignore[misc]
