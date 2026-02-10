"""Demo: async flow with penstock."""

import asyncio
import logging

from penstock import configure, current_flow_id, entrypoint, step

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s  [%(flow)s/%(step)s cid=%(correlation_id)s]",
)

configure("logging")


@entrypoint("async_pipeline")
async def ingest(payload: str) -> str:
    cid = current_flow_id()
    print(f"Ingesting '{payload}' (cid={cid})")
    result = await transform(payload)
    await store(result)
    return result


@step("async_pipeline", after="ingest")
async def transform(payload: str) -> str:
    print(f"  Transforming: {payload}")
    await asyncio.sleep(0.01)  # simulate async I/O
    return payload.upper()


@step("async_pipeline", after="transform")
async def store(data: str) -> None:
    print(f"  Storing: {data}")
    await asyncio.sleep(0.01)


if __name__ == "__main__":
    result = asyncio.run(ingest("hello world"))
    print(f"\nFinal result: {result}")
