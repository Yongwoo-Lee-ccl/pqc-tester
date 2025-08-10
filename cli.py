
import json, typer
from core.models import InputSpec
from core.router import route

app = typer.Typer(help="Unified estimator CLI (code-based via CAT, lattice via lattice-estimator).")

@app.command()
def estimate(spec_file: str):
    """Run estimation given an InputSpec JSON file.\"""
    with open(spec_file, "r") as f:
        payload = json.load(f)
    spec = InputSpec(**payload)
    adapter = route(spec)
    result = adapter.run(spec)
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    app()
