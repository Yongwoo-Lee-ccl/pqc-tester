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
    for name, attack in raw.get("attacks", {}).items():
        if "rop" in attack and attack["rop"] > 0:
            attack["log2_cost"] = math.log2(float(attack["rop"]))

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
    for name, attack in raw.get("attacks", {}).items():
        if "rop" in attack and attack["rop"] > 0:
            attack["log2_cost"] = math.log2(float(attack["rop"]))

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


def _expand_log2(value):
    """Expand a finite logarithm when a positive float can represent it."""
    try:
        expanded = 2.0 ** value
    except OverflowError:
        return None
    return expanded if math.isfinite(expanded) and expanded > 0 else None


def normalize_cryptographic(raw: dict):
    """Upstream complexities are already logarithms; never take log2 again."""
    meta = raw.get("meta", {})
    bound = meta.get("memory_bound")
    candidates = {}
    for name, attack in raw.get("attacks", {}).items():
        time = attack.get("log2_cost")
        memory = attack.get("log2_memory")
        if attack.get("error") or time is None or not math.isfinite(time):
            continue
        if bound is not None and (
            memory is None or not math.isfinite(memory) or memory > bound
        ):
            continue
        candidates[name] = attack
    if not candidates:
        raise ValueError(
            "No finite CryptographicEstimators attack satisfies the memory bound "
            f"(failures or unavailable attacks: {raw.get('attacks', {})})"
        )

    name = min(candidates, key=lambda key: candidates[key]["log2_cost"])
    attack = candidates[name]
    log2_memory = attack.get("log2_memory")
    mem_bytes = None
    if meta.get("memory_unit") == "bits" and log2_memory is not None:
        expanded = _expand_log2(log2_memory - 3)
        if expanded is not None:
            mem_bytes = math.ceil(expanded)

    return {
        "best_attack": name,
        "cost": {
            "rops": _expand_log2(attack["log2_cost"]),
            "log2_cost": attack["log2_cost"],
            "log2_memory": log2_memory,
            "mem_bytes": mem_bytes,
            "time_model": f"cryptographic-estimators:classical:{meta.get('time_unit')}",
        },
        "notes": (
            "Classical concrete estimates; log2_cost and log2_memory are base-2 "
            "logarithms in the units recorded in details.meta. The minimum covers "
            "only successful, applicable, non-excluded attacks within the memory bound."
        ),
    }
