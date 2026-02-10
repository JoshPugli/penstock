"""Demo: flow context metadata and correlation IDs."""

from penstock import (
    current_flow_id,
    entrypoint,
    flow,
    get_flow_context_value,
    set_flow_context_value,
    step,
)


@flow("context_demo")
class ContextDemo:
    @entrypoint
    def start(self, user: str) -> None:
        print(f"Correlation ID: {current_flow_id()}")

        # Attach metadata that downstream steps can read.
        set_flow_context_value("user", user)
        set_flow_context_value("source", "api")

        self.process()
        self.finish()

    @step(after="start")
    def process(self) -> None:
        user = get_flow_context_value("user")
        source = get_flow_context_value("source")
        print(f"  Processing for user={user}, source={source}")

        # Add more metadata.
        set_flow_context_value("processed", True)

    @step(after="process")
    def finish(self) -> None:
        processed = get_flow_context_value("processed", False)
        print(f"  Finishing (processed={processed})")


if __name__ == "__main__":
    ContextDemo().start("alice")
    print()
    ContextDemo().start("bob")
