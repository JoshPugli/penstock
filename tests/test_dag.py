"""Tests for penstock._dag.generate_dag."""

from __future__ import annotations

import pytest

from penstock._dag import generate_dag
from penstock._decorators import entrypoint, flow, step


class TestMermaidFormat:
    def test_simple_linear_flow(self) -> None:
        @flow("linear")
        class F:
            @entrypoint
            def start(self) -> None:
                pass

            @step(after="start")
            def process(self) -> None:
                pass

            @step(after="process")
            def finish(self) -> None:
                pass

        result = generate_dag("linear")
        assert "graph TD" in result
        assert "start --> process" in result
        assert "process --> finish" in result

    def test_branching_flow(self) -> None:
        @flow("branching")
        class F:
            @entrypoint
            def validate(self) -> None:
                pass

            @step(after="validate")
            def charge(self) -> None:
                pass

            @step(after="validate")
            def reserve(self) -> None:
                pass

            @step(after=["charge", "reserve"])
            def confirm(self) -> None:
                pass

        result = generate_dag("branching")
        assert "validate --> charge" in result
        assert "validate --> reserve" in result
        assert "charge --> confirm" in result
        assert "reserve --> confirm" in result

    def test_multiple_entrypoints(self) -> None:
        @flow("multi")
        class F:
            @entrypoint
            def api(self) -> None:
                pass

            @entrypoint
            def admin(self) -> None:
                pass

            @step(after=["api", "admin"])
            def process(self) -> None:
                pass

        result = generate_dag("multi")
        assert "admin --> process" in result
        assert "api --> process" in result

    def test_deterministic_output(self) -> None:
        @flow("det")
        class F:
            @entrypoint
            def a(self) -> None:
                pass

            @step(after="a")
            def c(self) -> None:
                pass

            @step(after="a")
            def b(self) -> None:
                pass

        r1 = generate_dag("det")
        r2 = generate_dag("det")
        assert r1 == r2

    def test_steps_without_edges(self) -> None:
        @flow("no_edges")
        class F:
            @entrypoint
            def start(self) -> None:
                pass

        result = generate_dag("no_edges")
        assert "graph TD" in result
        assert "start" in result

    def test_ends_with_newline(self) -> None:
        @flow("nl")
        class F:
            @entrypoint
            def start(self) -> None:
                pass

            @step(after="start")
            def end(self) -> None:
                pass

        result = generate_dag("nl")
        assert result.endswith("\n")


class TestOutputFile:
    def test_writes_to_file(self, tmp_path: object) -> None:
        import pathlib

        assert isinstance(tmp_path, pathlib.Path)

        @flow("file_out")
        class F:
            @entrypoint
            def start(self) -> None:
                pass

            @step(after="start")
            def end(self) -> None:
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
        @flow("f")
        class F:
            @entrypoint
            def start(self) -> None:
                pass

        with pytest.raises(ValueError, match="Unsupported format"):
            generate_dag("f", format="png")  # type: ignore[call-overload]
