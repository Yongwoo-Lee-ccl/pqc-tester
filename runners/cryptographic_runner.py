"""Run the optional, pure-Python CryptographicEstimators backend locally."""

import importlib
import json
import math
from importlib.metadata import version

from core.cryptographic_params import PARAM_MODELS


ESTIMATORS = {"mq": "MQ", "uov": "UOV", "mayo": "MAYO"}


def _load_backend(family):
    try:
        module = importlib.import_module(f"cryptographic_estimators.{family}Estimator")
        algorithms = importlib.import_module(
            f"cryptographic_estimators.{family}Estimator.{family}Algorithms"
        )
    except ImportError as error:
        raise RuntimeError(
            "CryptographicEstimators is unavailable. Install the backend with "
            "pip install -e '.[crypto-estimators]' "
            f"(import error: {error})"
        ) from error
    return getattr(module, f"{family}Estimator"), algorithms


def _log_value(value):
    if value is None or value == "--":
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def run_cryptographic_estimator(kind: str, params: dict) -> dict:
    if kind not in ESTIMATORS:
        raise ValueError(f"Unsupported CryptographicEstimators kind: {kind}")
    validated = PARAM_MODELS[kind].model_validate(params)
    # Preserve upstream defaults, notably MQ's expected solution count, and
    # distinguish an omitted theta from an explicitly supplied null.
    kwargs = validated.model_dump(exclude_unset=True)
    estimator_class, algorithms_module = _load_backend(ESTIMATORS[kind])
    excluded = kwargs.get("excluded_algorithms", [])
    known = {
        name: algorithm for name, algorithm in vars(algorithms_module).items()
        if isinstance(algorithm, type) and algorithm.__module__.startswith(
            algorithms_module.__name__ + "."
        )
    }
    unknown = set(excluded) - known.keys()
    if unknown:
        raise ValueError(
            f"Unknown excluded_algorithms for {kind}: {', '.join(sorted(unknown))}. "
            f"Choose from: {', '.join(sorted(known))}"
        )
    if "excluded_algorithms" in kwargs:
        kwargs["excluded_algorithms"] = [known[name] for name in excluded]
    estimator = estimator_class(**kwargs)
    attacks = {}
    for algorithm in estimator.algorithms():
        attack = {}
        attack_type = getattr(algorithm, "attack_type", None)
        if attack_type is not None:
            attack["attack_type"] = attack_type
        try:
            attack["log2_cost"] = _log_value(algorithm.time_complexity())
            attack["log2_memory"] = _log_value(algorithm.memory_complexity())
            attack["parameters"] = algorithm.get_optimal_parameters_dict()
        except (ArithmeticError, ValueError, TypeError, NotImplementedError) as error:
            # Preserve failures for inspection without discarding other attacks.
            attack["error"] = f"{type(error).__name__}: {error}"
        attacks[type(algorithm).__name__] = attack

    raw = {
        "attacks": attacks,
        "meta": {
            "backend": "cryptographic-estimators",
            "version": version("cryptographic-estimators"),
            "estimator": estimator_class.__name__,
            "params": params,
            "time_unit": "bit_operations" if validated.bit_complexities else "field_operations",
            "memory_unit": "bits" if validated.bit_complexities else "field_elements",
            "memory_bound": validated.memory_bound,
        },
    }
    # Optimal parameters can contain library-specific numbers; non-finite
    # diagnostics must also be valid JSON, rather than NaN or Infinity tokens.
    return json.loads(json.dumps(raw, default=str), parse_constant=lambda _: None)
