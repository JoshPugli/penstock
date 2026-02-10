"""Tests for penstock._dag.generate_dag."""

from __future__ import annotations

import pytest

from penstock._dag import generate_dag
from penstock._decorators import entrypoint, step


class TestMermaidFormat:
    def test_simple_linear_flow(self) -> None:
        @entrypoint("linear")
        def start() -> None:
            pass

        @step("linear", after="start")
        def process() -> None:
            pass

        @step("linear", after="process")
        def finish() -> None:
            pass

        result = generate_dag("linear")
        assert "graph TD" in result
        assert "start --> process" in result
        assert "process --> finish" in result

    def test_branching_flow(self) -> None:
        @entrypoint("branching")
        def validate() -> None:
            pass

        @step("branching", after="validate")
        def charge() -> None:
            pass

        @step("branching", after="validate")
        def reserve() -> None:
            pass

        @step("branching", after=["charge", "reserve"])
        def confirm() -> None:
            pass

        result = generate_dag("branching")
        assert "validate --> charge" in result
        assert "validate --> reserve" in result
        assert "charge --> confirm" in result
        assert "reserve --> confirm" in result

    def test_multiple_entrypoints(self) -> None:
        @entrypoint("multi")
        def api() -> None:
            pass

        @entrypoint("multi")
        def admin() -> None:
            pass

        @step("multi", after=["api", "admin"])
        def process() -> None:
            pass

        result = generate_dag("multi")
        assert "admin --> process" in result
        assert "api --> process" in result

    def test_deterministic_output(self) -> None:
        @entrypoint("det")
        def a() -> None:
            pass

        @step("det", after="a")
        def c() -> None:
            pass

        @step("det", after="a")
        def b() -> None:
            pass

        r1 = generate_dag("det")
        r2 = generate_dag("det")
        assert r1 == r2

    def test_steps_without_edges(self) -> None:
        @entrypoint("no_edges")
        def start() -> None:
            pass

        result = generate_dag("no_edges")
        assert "graph TD" in result
        assert "start" in result

    def test_ends_with_newline(self) -> None:
        @entrypoint("nl")
        def start() -> None:
            pass

        @step("nl", after="start")
        def end() -> None:
            pass

        result = generate_dag("nl")
        assert result.endswith("\n")


class TestOutputFile:
    def test_writes_to_file(self, tmp_path: object) -> None:
        import pathlib

        assert isinstance(tmp_path, pathlib.Path)

        @entrypoint("file_out")
        def start() -> None:
            pass

        @step("file_out", after="start")
        def end() -> None:
            pass

        out = tmp_path / "dag.md"
        result = generate_dag("file_out", output=str(out))
        assert result is None
        content = out.read_text()
        assert "start --> end" in content


class TestErrors:
    def test_unknown_flow_raises(self) -> None:
        with pytest.raises(KeyError, match="not_registered"):
            generate_dag("not_registered")

    def test_unsupported_format_raises(self) -> None:
        @entrypoint("f")
        def start() -> None:
            pass

        with pytest.raises(ValueError, match="Unsupported format"):
            generate_dag("f", format="png")  # type: ignore[call-overload]
