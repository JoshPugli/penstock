"""Demo: generate Mermaid DAGs for multiple flows."""

from penstock import entrypoint, generate_dag, step


# --- Flow 1: simple linear pipeline ---
@entrypoint("etl")
def extract() -> None: ...


@step("etl", after="extract")
def transform() -> None: ...


@step("etl", after="transform")
def load() -> None: ...


# --- Flow 2: branching with multiple entrypoints ---
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


# --- Flow 3: diamond dependency ---
@entrypoint("deploy")
def build() -> None: ...


@step("deploy", after="build")
def test_unit() -> None: ...


@step("deploy", after="build")
def test_integration() -> None: ...


@step("deploy", after=["test_unit", "test_integration"])
def deploy_staging() -> None: ...


@step("deploy", after="deploy_staging")
def deploy_prod() -> None: ...


if __name__ == "__main__":
    for name in ("etl", "user_update", "deploy"):
        print(f"## {name}\n")
        print("```mermaid")
        print(generate_dag(name), end="```\n\n")
