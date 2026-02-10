"""Demo: a simple order processing flow using penstock."""

import logging

from penstock import configure, current_flow_id, entrypoint, flow, generate_dag, step

# Set up logging so we can see penstock's structured output.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s  [%(flow)s/%(step)s cid=%(correlation_id)s]",
)

configure("logging")


@flow("order_processing")
class OrderFlow:
    @entrypoint
    def receive_order(self, order_id: str) -> dict[str, str]:
        print(f"\n--- Received order {order_id} (cid={current_flow_id()}) ---")
        data = self.validate(order_id)
        self.charge(data)
        self.ship(data)
        return data

    @step(after="receive_order")
    def validate(self, order_id: str) -> dict[str, str]:
        print(f"  Validating order {order_id}")
        return {"order_id": order_id, "status": "valid"}

    @step(after="validate")
    def charge(self, data: dict[str, str]) -> None:
        print(f"  Charging for order {data['order_id']}")

    @step(after="validate")
    def ship(self, data: dict[str, str]) -> None:
        print(f"  Shipping order {data['order_id']}")


if __name__ == "__main__":
    # --- Run the flow ---
    print("=== Running the flow ===\n")
    f = OrderFlow()
    f.receive_order("ORD-001")
    print()
    f.receive_order("ORD-002")

    # --- Generate the DAG ---
    print("\n=== Mermaid DAG ===\n")
    print(generate_dag("order_processing"))
