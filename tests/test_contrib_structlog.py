"""Tests for penstock.contrib.structlog.flow_processor."""

from __future__ import annotations

from typing import Any

from penstock._context import FlowContext, _set_context
from penstock.contrib.structlog import flow_processor


class TestFlowProcessor:
    def test_adds_flow_id_when_in_context(self) -> None:
        _set_context(FlowContext(correlation_id="test-cid"))
        event: dict[str, Any] = {"event": "something happened"}
        result = flow_processor(None, "info", event)
        assert result["flow_id"] == "test-cid"

    def test_omits_flow_id_when_no_context(self) -> None:
        event: dict[str, Any] = {"event": "something happened"}
        result = flow_processor(None, "info", event)
        assert "flow_id" not in result

    def test_preserves_existing_keys(self) -> None:
        _set_context(FlowContext(correlation_id="cid"))
        event: dict[str, Any] = {"event": "test", "user": "alice"}
        result = flow_processor(None, "info", event)
        assert result["user"] == "alice"
        assert result["event"] == "test"
        assert result["flow_id"] == "cid"

    def test_returns_same_dict(self) -> None:
        event: dict[str, Any] = {"event": "test"}
        result = flow_processor(None, "info", event)
        assert result is event
