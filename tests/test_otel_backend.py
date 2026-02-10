"""Tests for penstock.backends.otel.OTelBackend."""

from __future__ import annotations

import pytest

from penstock.backends.otel import OTelBackend


class TestOTelBackendWithoutPackage:
    def test_raises_without_otel_installed(self) -> None:
        with pytest.raises(RuntimeError, match="opentelemetry-api is required"):
            OTelBackend()

    def test_import_does_not_fail(self) -> None:
        # The module itself should be importable even without otel
        from penstock.backends.otel import OTelBackend as Cls

        assert Cls is not None
