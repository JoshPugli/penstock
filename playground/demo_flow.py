"""Demo: a simple order processing flow using penstock."""

import logging

from penstock import configure, current_flow_id, entrypoint, generate_dag, step

# Set up logging so we can see penstock's structured output.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s  [%(flow)s/%(step)s cid=%(correlation_id)s]",
)

configure("logging")


@entrypoint("order_processing")
def receive_order(order_id: str) -> dict[str, str]:
    print(f"\n--- Received order {order_id} (cid={current_flow_id()}) ---")
    data = validate(order_id)
    charge(data)
    ship(data)
    return data


@step("order_processing", after="receive_order")
def validate(order_id: str) -> dict[str, str]:
    print(f"  Validating order {order_id}")
    return {"order_id": order_id, "status": "valid"}


@step("order_processing", after="validate")
def charge(data: dict[str, str]) -> None:
    print(f"  Charging for order {data['order_id']}")


@step("order_processing", after="validate")
def ship(data: dict[str, str]) -> None:
    print(f"  Shipping order {data['order_id']}")


if __name__ == "__main__":
    # --- Run the flow ---
    print("=== Running the flow ===\n")
    receive_order("ORD-001")
    print()
    receive_order("ORD-002")

    # --- Generate the DAG ---
    print("\n=== Mermaid DAG ===\n")
    print(generate_dag("order_processing"))
