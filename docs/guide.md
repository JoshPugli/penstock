# Usage Guide

## Core Concepts

### Flows, Entrypoints, and Steps

A **flow** is a named group of related functions. An **entrypoint** is where a flow begins (e.g., an HTTP request handler, a Kafka consumer). A **step** is a function that runs after one or more predecessors.

```python
from penstock import entrypoint, step

@entrypoint("order_processing")
def receive_order(order_id: str) -> dict:
    data = validate(order_id)
    charge(data)
    ship(data)
    return data

@step("order_processing", after="receive_order")
def validate(order_id: str) -> dict:
    return {"order_id": order_id, "status": "valid"}

@step("order_processing", after="validate")
def charge(data: dict) -> None:
    ...

@step("order_processing", after="validate")
def ship(data: dict) -> None:
    ...
```

Key details:
- `@entrypoint("flow_name")` creates a fresh `FlowContext` (with a new correlation ID) on each call and resets it when the call finishes.
- `@step("flow_name", after=...)` reuses the existing `FlowContext`. It raises `RuntimeError` if called outside a flow.
- The flow name is passed as the first argument to both decorators — always use parentheses.
- `after=` accepts a string, a callable, or a list of either. It declares the DAG edge, not the execution order — your code still calls functions normally.
- Both sync and async functions are supported.
- Decorators work on any callable — standalone functions, methods, static methods, etc.

### Methods in a Class

You can use the decorators on class methods without any special class decorator:

```python
class OrderFlow:
    @entrypoint("order_processing")
    def receive_order(self, order_id: str) -> dict:
        data = self.validate(order_id)
        self.charge(data)
        return data

    @step("order_processing", after="receive_order")
    def validate(self, order_id: str) -> dict:
        return {"order_id": order_id, "status": "valid"}

    @step("order_processing", after="validate")
    def charge(self, data: dict) -> None:
        ...
```

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
from penstock import configure, current_flow_id, entrypoint, generate_dag, step

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s  [%(flow)s/%(step)s cid=%(correlation_id)s]",
)
configure("logging")

@entrypoint("order_processing")
def receive_order(order_id: str) -> dict:
    print(f"Received order {order_id} (cid={current_flow_id()})")
    data = validate(order_id)
    charge(data)
    ship(data)
    return data

@step("order_processing", after="receive_order")
def validate(order_id: str) -> dict:
    return {"order_id": order_id, "status": "valid"}

@step("order_processing", after="validate")
def charge(data: dict) -> None:
    print(f"Charging for order {data['order_id']}")

@step("order_processing", after="validate")
def ship(data: dict) -> None:
    print(f"Shipping order {data['order_id']}")

receive_order("ORD-001")

# Each call gets a unique correlation ID.
# All log entries within that call share the same ID.
```

### Multiple Entrypoints and Branching

```python
from penstock import entrypoint, generate_dag, step

@entrypoint("user_update")
def api_request() -> None: ...

@entrypoint("user_update")
def admin_action() -> None: ...

@step("user_update", after=["api_request", "admin_action"])
def validate() -> None: ...

@step("user_update", after="validate")
def persist() -> None: ...

@step("user_update", after="validate")
def notify() -> None: ...

@step("user_update", after=["persist", "notify"])
def audit_log() -> None: ...

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
    current_flow_id, entrypoint,
    get_flow_context_value, set_flow_context_value, step,
)

@entrypoint("context_demo")
def start(user: str) -> None:
    print(f"Correlation ID: {current_flow_id()}")
    set_flow_context_value("user", user)
    set_flow_context_value("source", "api")
    process()
    finish()

@step("context_demo", after="start")
def process() -> None:
    user = get_flow_context_value("user")
    source = get_flow_context_value("source")
    print(f"Processing for user={user}, source={source}")
    set_flow_context_value("processed", True)

@step("context_demo", after="process")
def finish() -> None:
    processed = get_flow_context_value("processed", False)
    print(f"Finishing (processed={processed})")

start("alice")
# Output:
#   Correlation ID: a1b2c3d4...
#   Processing for user=alice, source=api
#   Finishing (processed=True)
```

### Async Support

```python
import asyncio
from penstock import configure, current_flow_id, entrypoint, step

configure("logging")

@entrypoint("async_pipeline")
async def ingest(url: str) -> str:
    print(f"Ingesting {url} (cid={current_flow_id()})")
    return await transform(f"data from {url}")

@step("async_pipeline", after="ingest")
async def transform(raw: str) -> str:
    return raw.upper()

asyncio.run(ingest("https://example.com"))
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
├── _decorators.py       # @entrypoint, @step
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
