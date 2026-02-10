# Usage Guide

## Core Concepts

### Flows, Entrypoints, and Steps

A **flow** is a named group of related functions. An **entrypoint** is where a flow begins (e.g., an HTTP request handler, a Kafka consumer). A **step** is a function that runs after one or more predecessors.

```python
from penstock import flow, entrypoint, step

@flow("order_processing")
class OrderFlow:
    @entrypoint
    def receive_order(self, order_id: str) -> dict:
        data = self.validate(order_id)
        self.charge(data)
        self.ship(data)
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
```

Key details:
- `@flow(name)` is a **class decorator**. It scans the class for `@entrypoint`/`@step` markers and registers them.
- `@entrypoint` creates a fresh `FlowContext` (with a new correlation ID) on each call and resets it when the call finishes.
- `@step` reuses the existing `FlowContext`. It raises `RuntimeError` if called outside a flow.
- `after=` accepts a string, a callable, or a list of either. It declares the DAG edge, not the execution order — your code still calls functions normally.
- Both sync and async functions are supported.

### Correlation IDs

Every `@entrypoint` call generates a UUID-hex correlation ID. Retrieve it anywhere in the call stack:

```python
from penstock import current_flow_id

cid = current_flow_id()  # e.g. "a1b2c3d4e5f6..."
# Returns None if called outside a flow
```

The ID propagates via `contextvars`, so it works correctly with threads and async.

### Flow Context Metadata

You can attach arbitrary key-value metadata to the current flow and read it in downstream steps:

```python
from penstock import set_flow_context_value, get_flow_context_value

# In an entrypoint or step:
set_flow_context_value("user", "alice")
set_flow_context_value("source", "api")

# In a later step:
user = get_flow_context_value("user")       # "alice"
missing = get_flow_context_value("foo", 42)  # 42 (default)
```

### DAG Visualization

Generate a Mermaid diagram from any registered flow:

```python
from penstock import generate_dag

# Returns a string
diagram = generate_dag("order_processing")
print(diagram)
```

Output:
```
graph TD
    receive_order --> validate
    validate --> charge
    validate --> ship
```

Write directly to a file:
```python
generate_dag("order_processing", output="order_flow.md")
```

Only the `"mermaid"` format is currently supported.

---

## Examples

### Basic Flow with Logging Output

```python
import logging
from penstock import configure, current_flow_id, entrypoint, flow, generate_dag, step

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s  [%(flow)s/%(step)s cid=%(correlation_id)s]",
)
configure("logging")

@flow("order_processing")
class OrderFlow:
    @entrypoint
    def receive_order(self, order_id: str) -> dict:
        print(f"Received order {order_id} (cid={current_flow_id()})")
        data = self.validate(order_id)
        self.charge(data)
        self.ship(data)
        return data

    @step(after="receive_order")
    def validate(self, order_id: str) -> dict:
        return {"order_id": order_id, "status": "valid"}

    @step(after="validate")
    def charge(self, data: dict) -> None:
        print(f"Charging for order {data['order_id']}")

    @step(after="validate")
    def ship(self, data: dict) -> None:
        print(f"Shipping order {data['order_id']}")

f = OrderFlow()
f.receive_order("ORD-001")

# Each call gets a unique correlation ID.
# All log entries within that call share the same ID.
```

### Multiple Entrypoints and Branching

```python
from penstock import entrypoint, flow, generate_dag, step

@flow("user_update")
class UserUpdate:
    @entrypoint
    def api_request(self) -> None: ...

    @entrypoint
    def admin_action(self) -> None: ...

    @step(after=["api_request", "admin_action"])
    def validate(self) -> None: ...

    @step(after="validate")
    def persist(self) -> None: ...

    @step(after="validate")
    def notify(self) -> None: ...

    @step(after=["persist", "notify"])
    def audit_log(self) -> None: ...

print(generate_dag("user_update"))
```

Output:
```
graph TD
    admin_action --> validate
    api_request --> validate
    validate --> notify
    validate --> persist
    notify --> audit_log
    persist --> audit_log
```

### Context Metadata Passing

```python
from penstock import (
    current_flow_id, entrypoint, flow,
    get_flow_context_value, set_flow_context_value, step,
)

@flow("context_demo")
class ContextDemo:
    @entrypoint
    def start(self, user: str) -> None:
        print(f"Correlation ID: {current_flow_id()}")
        set_flow_context_value("user", user)
        set_flow_context_value("source", "api")
        self.process()
        self.finish()

    @step(after="start")
    def process(self) -> None:
        user = get_flow_context_value("user")
        source = get_flow_context_value("source")
        print(f"Processing for user={user}, source={source}")
        set_flow_context_value("processed", True)

    @step(after="process")
    def finish(self) -> None:
        processed = get_flow_context_value("processed", False)
        print(f"Finishing (processed={processed})")

ContextDemo().start("alice")
# Output:
#   Correlation ID: a1b2c3d4...
#   Processing for user=alice, source=api
#   Finishing (processed=True)
```

### Async Support

```python
import asyncio
from penstock import configure, current_flow_id, entrypoint, flow, step

configure("logging")

@flow("async_pipeline")
class AsyncPipeline:
    @entrypoint
    async def ingest(self, url: str) -> str:
        print(f"Ingesting {url} (cid={current_flow_id()})")
        return await self.transform(f"data from {url}")

    @step(after="ingest")
    async def transform(self, raw: str) -> str:
        return raw.upper()

asyncio.run(AsyncPipeline().ingest("https://example.com"))
```

---

## Project Structure

```
penstock/
├── __init__.py          # Public API re-exports
├── _types.py            # StepInfo, FlowInfo dataclasses
├── _context.py          # FlowContext + contextvars propagation
├── _registry.py         # Thread-safe flow registry
├── _config.py           # Backend configuration (configure/get_backend/reset)
├── _decorators.py       # @flow, @entrypoint, @step
├── _dag.py              # generate_dag() — Mermaid output
├── backends/
│   ├── base.py          # TracingBackend ABC
│   ├── logging.py       # LoggingBackend (default, zero deps)
│   └── otel.py          # OTelBackend (requires opentelemetry)
└── contrib/
    ├── django.py        # FlowMiddleware
    ├── celery.py        # flow_task + install_celery_signals
    └── structlog.py     # flow_processor
```
