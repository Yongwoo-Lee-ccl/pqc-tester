
from .base import Adapter
from core.models import InputSpec, Result, AttackCost
from runners.cat_runner import run_cat
from core.normalizer import normalize_cat

class CatAdapter(Adapter):
    def run(self, spec: InputSpec) -> Result:
        raw = run_cat(spec.params)
        norm = normalize_cat(raw)
        return Result(
            kind="code",
            label=spec.label,
            best_attack=norm["best_attack"],
            cost=AttackCost(**norm["cost"]),
            details=raw,
            notes=norm.get("notes")
        )
