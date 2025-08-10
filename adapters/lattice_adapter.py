
from .base import Adapter
from core.models import InputSpec, Result, AttackCost
from runners.sage_runner import run_estimator
from core.normalizer import normalize_lwe

class LatticeAdapter(Adapter):
    def run(self, spec: InputSpec) -> Result:
        raw = run_estimator(spec.params)
        norm = normalize_lwe(raw)
        return Result(
            kind="lattice",
            label=spec.label,
            best_attack=norm["best_attack"],
            cost=AttackCost(**norm["cost"]),
            details=raw,
            notes=norm.get("notes")
        )
