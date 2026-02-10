"""Demo: flow context metadata and correlation IDs."""

from penstock import (
    current_flow_id,
    entrypoint,
    get_flow_context_value,
    set_flow_context_value,
    step,
)


@entrypoint("context_demo")
def start(user: str) -> None:
    print(f"Correlation ID: {current_flow_id()}")

    # Attach metadata that downstream steps can read.
    set_flow_context_value("user", user)
    set_flow_context_value("source", "api")

    process()
    finish()


@step("context_demo", after="start")
def process() -> None:
    user = get_flow_context_value("user")
    source = get_flow_context_value("source")
    print(f"  Processing for user={user}, source={source}")

    # Add more metadata.
    set_flow_context_value("processed", True)


@step("context_demo", after="process")
def finish() -> None:
    processed = get_flow_context_value("processed", False)
    print(f"  Finishing (processed={processed})")


if __name__ == "__main__":
    start("alice")
    print()
    start("bob")
