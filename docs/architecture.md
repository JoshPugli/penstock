# Architecture & Design

## Why penstock exists alongside OpenTelemetry

OpenTelemetry answers the question: **what happened on this specific request?** It gives you spans, waterfall traces, and latency data for individual operations at runtime.

Penstock answers a different question: **what are all the possible paths through my system?** Flow definitions via decorators produce a static DAG at import time — living architecture documentation that stays in sync with your code because it *is* your code.

These are complementary. Penstock provides the developer-facing API (clean decorators, flow definitions, DAG visualization) while OTel can serve as the backend that handles the actual tracing mechanics. Developers think in terms of flows and steps. Penstock translates that into real OTel spans when available, or falls back to structured logging when it isn't.

## Pluggable backends

Penstock separates **flow declaration** (what runs, in what order) from **trace emission** (how that execution is recorded). See [Backends](backends.md) for the full backend API and available implementations.

## Gradual adoption path

Penstock is designed to be useful from day one without any tracing infrastructure, and to scale up as your observability stack matures.

### Phase 1: Structured logging

Install penstock, decorate your pipeline, and get correlation IDs in your existing log aggregator immediately. No new infrastructure required.

```python
@flow("bom_sync")
@entrypoint
def handle_kafka_message(msg):
    part_number = msg.payload["part_number"]
    return sync_reference(part_number)

@flow("bom_sync")
@step(after="handle_kafka_message")
def sync_reference(part_number):
    data = fetch_from_api(part_number)
    return upsert_to_db(data)
```

Query your logs:

```
correlation_id="abc-123" | sort timestamp
```

You see an ordered list of steps with durations — enough to identify bottlenecks.

### Phase 2: DAG documentation

Use the static DAG generation to produce architecture diagrams that stay in sync with code. Add this to CI to auto-generate documentation on every merge.

```python
from penstock import generate_dag

generate_dag("bom_sync", format="mermaid")
```

```mermaid
graph TD
    handle_kafka_message --> sync_reference
    sync_reference --> upsert_to_db
    upsert_to_db --> publish_change_events
    publish_change_events --> update_ebom
    publish_change_events --> enqueue_changelog
```

### Phase 3: OpenTelemetry traces

When your team adopts a trace backend (Tempo, Jaeger, Datadog), switch the penstock backend:

```python
penstock.configure(backend="otel")
```

Every decorated function now emits real spans with parent-child hierarchy. The same decorators, the same code, but now you get waterfall visualizations and cross-service trace propagation.

### Phase 4: Cross-process propagation

For flows that span Celery tasks, Kafka consumers, or gRPC calls, penstock's contrib integrations handle context propagation automatically.

```python
from penstock.contrib.celery import flow_task

@flow("bom_sync")
@flow_task(after="publish_change_events")
def create_change_logs(changelog_dicts):
    # Trace ID propagated automatically via Celery headers
    # Appears as a child span of publish_change_events in your trace viewer
    ...
```

## Design boundaries

Penstock intentionally does **not** do the following:

- **Metrics or alerting.** Use Prometheus, Datadog, or your existing metrics stack. Penstock is about flow structure and tracing, not aggregation.
- **Sampling or tail-based collection.** That's the OTel Collector's job. Penstock emits spans; your collector decides what to keep.
- **Auto-instrumentation of libraries.** OTel already has instrumentors for Django, psycopg2, gRPC, Redis, etc. Penstock instruments *your* application logic — the business flow layer that sits above library calls.
- **Span storage or querying.** Penstock generates traces; Tempo/Jaeger/Splunk stores and queries them.

The goal is to stay in the **flow definition and developer experience** layer, and delegate everything else to purpose-built tools.
