
import math
from typing import Dict, Tuple, Optional

def _best(attacks: Dict[str, dict]) -> Tuple[Optional[str], Optional[dict]]:
    best_name, best = None, None
    for name, a in attacks.items():
        if "rop" not in a:
            continue
        if best is None or float(a["rop"]) < float(best["rop"]):
            best_name, best = name, a
    return best_name, best

def normalize_lwe(raw: dict):
    name, a = _best(raw.get("attacks", {}))
    if not a:
        raise ValueError("No attack with 'rop' found in lattice-estimator output")
    rops = float(a["rop"])
    succ = a.get("succ") or a.get("p_success")  # tolerate different keys
    return {
        "best_attack": name or "unknown",
        "cost": {
            "rops": rops,
            "log2_cost": math.log2(rops),
            "success_prob": float(succ) if succ is not None else None
        },
        "notes": raw.get("notes")
    }

def normalize_cat(raw: dict):
    name, a = _best(raw.get("attacks", {}))
    if not a:
        raise ValueError("No attack with 'rop' found in CAT output")
    rops = float(a["rop"])
    succ = a.get("succ") or a.get("p_success")
    return {
        "best_attack": name or "unknown",
        "cost": {
            "rops": rops,
            "log2_cost": math.log2(rops),
            "success_prob": float(succ) if succ is not None else None
        },
        "notes": raw.get("meta", {}).get("model")
    }
