import json
import math
import subprocess
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from adapters.cat_adapter import CatAdapter
from adapters.cryptographic_adapter import CryptographicAdapter
from adapters.lattice_adapter import LatticeAdapter
from core.cryptographic_params import MQParams, UOVParams, MAYOParams
from core.models import AttackCost, InputSpec
from core.normalizer import normalize_cryptographic
from core.router import route
from runners import cryptographic_runner as runner


@pytest.mark.parametrize("kind, adapter", [
    ("code", CatAdapter), ("lattice", LatticeAdapter),
    ("mq", CryptographicAdapter), ("uov", CryptographicAdapter),
    ("mayo", CryptographicAdapter),
])
def test_routing(kind, adapter):
    assert isinstance(route(InputSpec(kind=kind, label="test", params={})), adapter)


def test_router_does_not_import_optional_library():
    subprocess.run([
        sys.executable, "-c",
        "import sys; from core.router import route; "
        "assert not any(n.startswith('cryptographic_estimators') for n in sys.modules)",
    ], check=True)


@pytest.mark.parametrize("kind, module, runner_name", [
    ("code", "adapters.cat_adapter", "run_cat"),
    ("lattice", "adapters.lattice_adapter", "run_estimator"),
])
def test_existing_adapters_keep_operation_costs(monkeypatch, kind, module, runner_name):
    monkeypatch.setattr(f"{module}.{runner_name}", lambda _: {
        "attacks": {"existing_attack": {"rop": 1024, "succ": 0.75}},
    })
    spec = InputSpec(kind=kind, label="existing", params={})
    result = route(spec).run(spec)
    assert result.kind == kind
    assert result.best_attack == "existing_attack"
    assert result.cost.rops == 1024
    assert result.cost.log2_cost == 10
    assert result.cost.success_prob == 0.75


@pytest.mark.parametrize("update", [
    {"n": 0}, {"m": -1}, {"q": 1}, {"n": 15.5}, {"n": True},
    {"q": "2"}, {"w": 3.1}, {"theta": 3}, {"memory_bound": -1},
    {"memory_bound": math.inf}, {"w": math.nan}, {"memory_access": 4},
    {"bit_complexities": 2}, {"nsolutions": -1},
    {"complexity_type": 1}, {"include_quantum": True}, {"typo": 10},
])
def test_invalid_parameters_fail_before_loading_backend(monkeypatch, update):
    def unexpected_load(*args):
        pytest.fail("Invalid parameters must fail before importing the backend")
    monkeypatch.setattr(runner, "_load_backend", unexpected_load)
    with pytest.raises(ValidationError):
        runner.run_cryptographic_estimator("mq", dict(n=15, m=17, q=2) | update)


def test_preserve_upstream_defaults_and_explicit_null():
    default = MQParams(n=15, m=17, q=2).model_dump(exclude_unset=True)
    assert default == {"n": 15, "m": 17, "q": 2}
    assert MQParams(n=15, m=17, q=2, theta=None).model_dump(exclude_unset=True)["theta"] is None
    assert MAYOParams(n=16, m=12, o=4, k=2, q=16).theta is None


@pytest.mark.parametrize("model, params", [
    (UOVParams, dict(n=10, m=10, q=2)),
    (MAYOParams, dict(n=16, m=16, o=4, k=2, q=16)),
    (MAYOParams, dict(n=16, m=12, o=4, k=12, q=16)),
    (MAYOParams, dict(n=16, m=12, o=4, k=0, q=16)),
])
def test_invalid_scheme_dimensions(model, params):
    with pytest.raises(ValidationError):
        model(**params)


def test_missing_backend_has_install_hint(monkeypatch):
    def missing(*args):
        raise ModuleNotFoundError("No module named cryptographic_estimators")
    monkeypatch.setattr(runner.importlib, "import_module", missing)
    with pytest.raises(RuntimeError, match=r"pip install -e '.\[crypto-estimators\]'"):
        runner.run_cryptographic_estimator("mq", dict(n=15, m=17, q=2))


def raw_attacks(attacks, **meta):
    return {"attacks": attacks, "meta": {
        "time_unit": "bit_operations", "memory_unit": "bits", **meta,
    }}


def test_normalization_uses_log_cost_and_retains_units():
    raw = raw_attacks({
        "slow": {"log2_cost": 140.5, "log2_memory": 80},
        "best": {"log2_cost": 128.25, "log2_memory": 10.5},
        "unavailable": {"log2_cost": None},
        "failed": {"log2_cost": 1, "error": "failed"},
        "infinite": {"log2_cost": math.inf},
        "nan": {"log2_cost": math.nan},
    })
    norm = normalize_cryptographic(raw)
    cost = AttackCost(**norm["cost"])
    assert norm["best_attack"] == "best"
    assert cost.log2_cost == 128.25
    assert cost.rops == 2 ** 128.25
    assert cost.log2_memory == 10.5
    assert cost.mem_bytes == math.ceil(2 ** 10.5 / 8)
    assert cost.success_prob is None
    assert cost.time_model.endswith(":bit_operations")
    assert "rop" not in raw["attacks"]["best"]  # normalization does not mutate inputs


def test_memory_bound_filters_even_fixed_parameter_attacks():
    norm = normalize_cryptographic(raw_attacks({
        "fast_but_large": {"log2_cost": 10, "log2_memory": 101},
        "missing_memory": {"log2_cost": 1},
        "fits": {"log2_cost": 20, "log2_memory": 100},
    }, memory_bound=100))
    assert norm["best_attack"] == "fits"


@pytest.mark.parametrize("attacks", [
    {}, {"unavailable": {"log2_cost": None}},
    {"too_large": {"log2_cost": 10, "log2_memory": 101}},
])
def test_no_finite_feasible_attack_is_an_error(attacks):
    with pytest.raises(ValueError, match="No finite CryptographicEstimators attack"):
        normalize_cryptographic(raw_attacks(attacks, memory_bound=100))


def test_large_log_costs_remain_usable_and_valid_json():
    cost = AttackCost(**normalize_cryptographic(raw_attacks({
        "large": {"log2_cost": 2048, "log2_memory": 2048},
    }))["cost"])
    assert cost.log2_cost == 2048
    assert cost.log2_memory == 2048
    assert cost.rops is None
    assert cost.mem_bytes is None
    assert json.loads(cost.model_dump_json())["log2_cost"] == 2048


def test_field_elements_are_not_reported_as_bytes():
    norm = normalize_cryptographic(raw_attacks({
        "basic": {"log2_cost": 30, "log2_memory": 12},
    }, time_unit="field_operations", memory_unit="field_elements"))
    assert norm["cost"]["mem_bytes"] is None
    assert norm["cost"]["log2_memory"] == 12
    assert norm["cost"]["time_model"].endswith(":field_operations")


def test_algorithm_failure_does_not_discard_other_estimates(monkeypatch):
    class Broken:
        def time_complexity(self):
            raise NotImplementedError("not supported")

    class Working:
        attack_type = "forgery"

        def time_complexity(self):
            return 25.5

        def memory_complexity(self):
            return 10

        def get_optimal_parameters_dict(self):
            return {"k": 2, "diagnostic": math.inf}

    class FakeEstimator:
        def __init__(self, **kwargs):
            assert kwargs == {"n": 24, "m": 10, "q": 2}

        def algorithms(self):
            return [Broken(), Working()]

    monkeypatch.setattr(runner, "_load_backend", lambda _: (FakeEstimator, SimpleNamespace(__name__="fake")))
    monkeypatch.setattr(runner, "version", lambda _: "test")
    spec = InputSpec(kind="uov", label="test", params=dict(n=24, m=10, q=2))
    result = route(spec).run(spec)
    assert result.best_attack == "Working"
    assert result.details["attacks"]["Broken"]["error"] == "NotImplementedError: not supported"
    assert result.details["attacks"]["Working"]["attack_type"] == "forgery"
    assert result.details["attacks"]["Working"]["parameters"]["diagnostic"] is None
    json.dumps(result.model_dump(), allow_nan=False)
