# Integrations

## Django

Middleware that creates a `FlowContext` per request and adds an `X-Correlation-ID` response header:

```python
# settings.py
MIDDLEWARE = [
    "penstock.contrib.django.FlowMiddleware",
    ...
]
```

Every view and downstream function call within the request has access to the correlation ID via `current_flow_id()`. The context is automatically cleaned up after the response, even on exceptions.

## Celery

Propagates correlation IDs across task boundaries:

```python
from penstock.contrib.celery import flow_task, install_celery_signals

# Option 1: decorator-based (manual header management)
@flow_task
def my_task(data):
    print(current_flow_id())  # correlation ID from the caller

# Option 2: automatic via signals (call once at startup)
install_celery_signals()
```

### Sending correlation IDs with tasks

The `@flow_task` decorator adds a `_penstock_headers()` helper to the wrapped function. Use it to forward the current correlation ID when dispatching a task:

```python
@flow_task
def my_task(data):
    ...

# Inside a flow, get headers to propagate:
headers = my_task._penstock_headers()
# {"penstock_correlation_id": "abc123..."} or {} if outside a flow

# Pass when calling:
my_task(__penstock_headers__=headers)
```

## structlog

Processor that injects `flow_id` into every log entry during an active flow:

```python
import structlog
from penstock.contrib.structlog import flow_processor

structlog.configure(
    processors=[
        flow_processor,  # Adds flow_id to all log entries
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)
```

When no flow is active, the `flow_id` key is omitted rather than set to `None`, keeping logs clean outside of flow contexts.

```bash
pip install penstock[structlog]
```
