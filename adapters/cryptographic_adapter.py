from .base import Adapter
from core.models import AttackCost, InputSpec, Result
from core.normalizer import normalize_cryptographic
from runners.cryptographic_runner import run_cryptographic_estimator


class CryptographicAdapter(Adapter):
    def run(self, spec: InputSpec) -> Result:
        raw = run_cryptographic_estimator(spec.kind, spec.params)
        norm = normalize_cryptographic(raw)
        return Result(
            kind=spec.kind,
            label=spec.label,
            best_attack=norm["best_attack"],
            cost=AttackCost(**norm["cost"]),
            details=raw,
            notes=norm["notes"],
        )
