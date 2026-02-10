"""Demo: generate Mermaid DAGs for multiple flows."""

from penstock import entrypoint, flow, generate_dag, step


# --- Flow 1: simple linear pipeline ---
@flow("etl")
class ETL:
    @entrypoint
    def extract(self) -> None: ...

    @step(after="extract")
    def transform(self) -> None: ...

    @step(after="transform")
    def load(self) -> None: ...


# --- Flow 2: branching with multiple entrypoints ---
@flow("user_update")
class UserUpdate:
    @entrypoint
    def api_request(self) -> None: ...

    @entrypoint
    def admin_action(self) -> None: ...

    @step(after=["api_request", "admin_action"])
    def validate(self) -> None: ...

    @step(after="validate")
    def persist(self) -> None: ...

    @step(after="validate")
    def notify(self) -> None: ...

    @step(after=["persist", "notify"])
    def audit_log(self) -> None: ...


# --- Flow 3: diamond dependency ---
@flow("deploy")
class Deploy:
    @entrypoint
    def build(self) -> None: ...

    @step(after="build")
    def test_unit(self) -> None: ...

    @step(after="build")
    def test_integration(self) -> None: ...

    @step(after=["test_unit", "test_integration"])
    def deploy_staging(self) -> None: ...

    @step(after="deploy_staging")
    def deploy_prod(self) -> None: ...


if __name__ == "__main__":
    for name in ("etl", "user_update", "deploy"):
        print(f"## {name}\n")
        print("```mermaid")
        print(generate_dag(name), end="```\n\n")
