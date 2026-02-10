# penstock

A lightweight Python library for defining, tracing, and visualizing application flows.

## What is penstock?

Penstock lets you declaratively define how data flows through your application — from entrypoints like HTTP requests or Kafka messages, through processing steps, to side effects. It provides:

- **Correlation IDs** for grouping logs and traces across a single operation
- **Flow definitions** via decorators that double as living documentation
- **DAG visualization** to see all possible paths through your system at a glance

Describe flows that already exist in your code, get correlation IDs automatically, and generate static documentation of all possible paths — without changing how your code executes or adding infrastructure.

## Installation

```bash
# Core (zero dependencies)
pip install penstock

# With OpenTelemetry support
pip install penstock[otel]

# With structlog support
pip install penstock[structlog]
```

Requires Python 3.14+.

## Quick Start

```python
from penstock import flow, entrypoint, step, current_flow_id, generate_dag

@flow("order_processing")
class OrderFlow:
    @entrypoint
    def receive_order(self, order_id: str) -> dict:
        print(f"Order {order_id} (cid={current_flow_id()})")
        data = self.validate(order_id)
        self.charge(data)
        return data

    @step(after="receive_order")
    def validate(self, order_id: str) -> dict:
        return {"order_id": order_id, "status": "valid"}

    @step(after="validate")
    def charge(self, data: dict) -> None:
        ...

    @step(after="validate")
    def ship(self, data: dict) -> None:
        ...

OrderFlow().receive_order("ORD-001")
# Every step shares the same correlation ID for log filtering.

print(generate_dag("order_processing"))
# graph TD
#     receive_order --> validate
#     validate --> charge
#     validate --> ship
```

## Design Goals

1. **Minimal overhead** — decorators are cheap, context propagation uses `contextvars`
2. **Zero magic** — your functions remain normal functions, callable without penstock
3. **Static analysis** — DAG is built at import time, not runtime
4. **Framework agnostic** — works with Django, Flask, FastAPI, Celery, or plain Python

## Documentation

- **[Usage Guide](docs/guide.md)** — core concepts, examples, context metadata, async support
- **[Backends](docs/backends.md)** — logging, OpenTelemetry, auto-detection, custom backends
- **[Integrations](docs/integrations.md)** — Django, Celery, structlog
- **[Architecture](docs/architecture.md)** — design philosophy, adoption path, design boundaries

## License

MIT
