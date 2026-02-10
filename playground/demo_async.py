"""Demo: async flow with penstock."""

import asyncio
import logging

from penstock import configure, current_flow_id, entrypoint, flow, step

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s  [%(flow)s/%(step)s cid=%(correlation_id)s]",
)

configure("logging")


@flow("async_pipeline")
class AsyncPipeline:
    @entrypoint
    async def ingest(self, payload: str) -> str:
        cid = current_flow_id()
        print(f"Ingesting '{payload}' (cid={cid})")
        result = await self.transform(payload)
        await self.store(result)
        return result

    @step(after="ingest")
    async def transform(self, payload: str) -> str:
        print(f"  Transforming: {payload}")
        await asyncio.sleep(0.01)  # simulate async I/O
        return payload.upper()

    @step(after="transform")
    async def store(self, data: str) -> None:
        print(f"  Storing: {data}")
        await asyncio.sleep(0.01)


if __name__ == "__main__":
    p = AsyncPipeline()
    result = asyncio.run(p.ingest("hello world"))
    print(f"\nFinal result: {result}")
