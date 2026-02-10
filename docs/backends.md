# Backends

Penstock separates flow declaration from trace emission via pluggable backends. The `@entrypoint` and `@step` decorators always do two things:

1. **Import time** — register the step in a flow registry used for static DAG generation. This happens regardless of backend.
2. **Runtime** — delegate to a configurable `TracingBackend` that decides how to record the execution.

## Configuration

```python
import penstock

# Structured logging (default, no dependencies)
penstock.configure(backend="logging")

# OpenTelemetry (requires opentelemetry-sdk)
penstock.configure(backend="otel")

# Custom backend instance
penstock.configure(backend=MyCustomBackend())
```

## Auto-detection

If you don't call `configure()`, penstock auto-detects on first use: it tries to create an `OTelBackend`, and if `opentelemetry` isn't installed, falls back to `LoggingBackend`.

## LoggingBackend (default)

No dependencies beyond the standard library. Uses `contextvars` for correlation ID propagation and emits structured log entries with timing data.

```python
from penstock import configure
configure("logging")
```

Emits `step.start` and `step.end` log records with `flow`, `step`, `correlation_id`, and `duration_ms` extras. Sufficient for debugging with Splunk, ELK, or any log aggregator that supports structured JSON. Filter by `correlation_id` to see every step in a single flow invocation.

### Implementation

```python
class LoggingBackend(TracingBackend):
    @contextmanager
    def span(self, step_name, flow_name, **attrs):
        cid = _correlation_id.get()
        if not cid:
            cid = str(uuid.uuid4())
            _correlation_id.set(cid)

        start = time.monotonic()
        try:
            yield
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "%s completed",
                step_name,
                extra={
                    "correlation_id": cid,
                    "flow": flow_name,
                    "step": step_name,
                    "duration_ms": round(elapsed_ms, 2),
                    **attrs,
                },
            )

    def get_correlation_id(self) -> str:
        return _correlation_id.get()
```

## OTelBackend

Creates real OpenTelemetry spans with proper parent-child hierarchy. The correlation ID becomes the OTel trace ID (32-char hex). Requires `opentelemetry-api` and `opentelemetry-sdk`.

```bash
pip install penstock[otel]
```

```python
from penstock import configure
configure("otel")
```

Each step becomes a span with a `penstock.flow` attribute. When this backend is active, all `@step` decorators automatically produce spans visible in Tempo, Jaeger, or any OTel-compatible trace viewer — no code changes at call sites.

### Implementation

```python
class OTelBackend(TracingBackend):
    @contextmanager
    def span(self, step_name, flow_name, **attrs):
        with tracer.start_as_current_span(
            step_name,
            attributes={"penstock.flow": flow_name, **attrs},
        ) as otel_span:
            yield otel_span

    def get_correlation_id(self) -> str:
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            return format(ctx.trace_id, "032x")
        return ""
```

## Custom Backends

Subclass `TracingBackend` and pass an instance:

```python
from penstock.backends import TracingBackend
from penstock import configure

class MyBackend(TracingBackend):
    def span(self, step_name, flow_name, **attrs):
        ...  # your context manager

    def get_correlation_id(self):
        ...  # return current correlation ID

configure(backend=MyBackend())
```

### TracingBackend ABC

```python
from abc import ABC, abstractmethod
from contextlib import contextmanager

class TracingBackend(ABC):
    @abstractmethod
    @contextmanager
    def span(self, step_name: str, flow_name: str, **attrs) -> Any:
        """Wrap a step execution in a traceable span."""
        ...

    @abstractmethod
    def get_correlation_id(self) -> str:
        """Return the current correlation/trace ID."""
        ...
```
