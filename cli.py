
import json, typer
import math
from core.models import InputSpec
from core.router import route

app = typer.Typer(help="Unified estimator CLI (code-based via CAT, lattice via lattice-estimator).")

def validate_code_params(params):
    """Validate code-based parameters against CAT constraints (section 4.6)."""
    n = params.get('n')
    k = params.get('k') 
    t = params.get('t')
    
    if not all(x is not None for x in [n, k, t]):
        return  # Skip validation if params incomplete
    
    # CAT uniformmatrix constraints from section 4.6:
    # 1. n ≥ 8
    # 2. 0.7n ≤ k ≤ 0.8n (rate constraint)
    # 3. k = n - t⌈log₂(n)⌉ (structural constraint)
    
    lgq = math.ceil(math.log2(n)) if n > 1 else 1
    
    # Check basic constraints
    if n < 8:
        typer.echo(f"⚠️  Warning: n={n} < 8. CAT requires n ≥ 8.")
        return
    
    # Check rate constraint: 0.7n ≤ k ≤ 0.8n
    rate_min, rate_max = 0.7 * n, 0.8 * n
    if not (rate_min <= k <= rate_max):
        typer.echo(f"⚠️  Warning: k={k} violates CAT rate constraint 0.7n ≤ k ≤ 0.8n")
        typer.echo(f"   Required range: {rate_min:.1f} ≤ k ≤ {rate_max:.1f}")
    
    # Check structural constraint k = n - t⌈log₂(n)⌉
    cat_k = n - t * lgq
    if k != cat_k:
        typer.echo(f"⚠️  Warning: k={k} doesn't match CAT's structural constraint")
        typer.echo(f"   CAT formula: k = n - t⌈log₂(n)⌉ = {n} - {t}×{lgq} = {cat_k}")
        typer.echo(f"   CAT will use k={cat_k} instead of your requested k={k}")
    
    # Check if the resulting k satisfies rate constraint
    if not (rate_min <= cat_k <= rate_max):
        typer.echo(f"⚠️  Warning: For t={t}, CAT calculates k={cat_k} which violates rate constraint")
        typer.echo(f"   CAT may adjust t to find valid parameters")

@app.command()
def estimate(spec_file: str):
    """Run estimation given an InputSpec JSON file."""
    with open(spec_file, "r") as f:
        payload = json.load(f)
    spec = InputSpec(**payload)
    
    # Validate code-based parameters
    if spec.kind == "code":
        validate_code_params(spec.params)
    
    adapter = route(spec)
    result = adapter.run(spec)
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    app()
