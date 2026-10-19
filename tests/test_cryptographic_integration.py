"""Compare the wrapper with the upstream public API, without external services."""

import json
import math
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

ce = pytest.importorskip("cryptographic_estimators")

from cli import app
from core.models import InputSpec
from core.router import route
from runners.cryptographic_runner import run_cryptographic_estimator

pytestmark = pytest.mark.integration
PRESETS = Path(__file__).resolve().parents[1] / "presets"


REAL_PRESET_MARK = pytest.mark.skipif(
    os.environ.get("PQC_TEST_REAL_PRESETS") != "1",
    reason="Set PQC_TEST_REAL_PRESETS=1 for full-size candidate comparisons",
)


@pytest.mark.parametrize("preset, kind, estimator", [
    ("mq-small", "mq", ce.MQEstimator),
    ("uov-small", "uov", ce.UOVEstimator),
    ("mayo-small", "mayo", ce.MAYOEstimator),
    *[
        pytest.param(preset, kind, estimator, marks=REAL_PRESET_MARK)
        for kind, estimator, names in [
            ("uov", ce.UOVEstimator, ["uov-ip", "uov-is", "uov-iii", "uov-v"]),
            ("mayo", ce.MAYOEstimator, ["mayo1", "mayo2", "mayo3", "mayo5"]),
        ]
        for preset in names
    ],
])
def test_preset_cli_matches_upstream(preset, kind, estimator):
    path = PRESETS / f"{preset}.json"
    spec = json.loads(path.read_text())
    upstream = estimator(**spec["params"]).estimate()
    available = {
        name: attack["estimate"] for name, attack in upstream.items()
        if isinstance(attack["estimate"]["time"], (float, int))
        and math.isfinite(attack["estimate"]["time"])
    }
    best = min(available, key=lambda name: available[name]["time"])
    output = CliRunner().invoke(app, [str(path)])
    assert output.exit_code == 0, output.output
    result = json.loads(output.stdout)
    assert result["kind"] == kind
    assert result["label"] == spec["label"]
    assert result["best_attack"] == best
    assert result["cost"]["log2_cost"] == pytest.approx(available[best]["time"])
    assert result["cost"]["log2_memory"] == pytest.approx(available[best]["memory"])
    assert result["details"]["meta"]["version"] == "2.1.1"
    assert set(result["details"]["attacks"]) == set(upstream)
    for name, attack in result["details"]["attacks"].items():
        time = upstream[name]["estimate"]["time"]
        if isinstance(time, (float, int)) and math.isfinite(time):
            assert attack["log2_cost"] == pytest.approx(time)
        else:
            assert attack["log2_cost"] is None
        if kind != "mq":
            assert attack["attack_type"] == upstream[name][" "]["attack_type"]
    json.dumps(result, allow_nan=False)


def test_options_and_exclusion_match_upstream():
    params = dict(n=15, m=17, q=3, w=2, theta=None, bit_complexities=0,
                  memory_access=1, excluded_algorithms=["ExhaustiveSearch"])
    from cryptographic_estimators.MQEstimator.MQAlgorithms import ExhaustiveSearch
    expected = ce.MQEstimator(**(params | {"excluded_algorithms": [ExhaustiveSearch]})).estimate()
    spec = InputSpec(kind="mq", label="options", params=params)
    result = route(spec).run(spec)
    assert "ExhaustiveSearch" not in result.details["attacks"]
    for name, attack in result.details["attacks"].items():
        assert attack["log2_cost"] == pytest.approx(expected[name]["estimate"]["time"])
    assert result.cost.mem_bytes is None
    assert result.details["meta"]["memory_unit"] == "field_elements"


def test_unknown_algorithm_name_is_rejected():
    with pytest.raises(ValueError, match="Unknown excluded_algorithms for mq: Typo"):
        run_cryptographic_estimator("mq", dict(n=15, m=17, q=2, excluded_algorithms=["Typo"]))


def test_underdefined_mq_preserves_expected_solution_default():
    params = dict(n=20, m=15, q=3)
    expected = ce.MQEstimator(**params).estimate()
    raw = run_cryptographic_estimator("mq", params)
    for name, attack in raw["attacks"].items():
        time = expected[name]["estimate"]["time"]
        if time == "--":
            assert attack["log2_cost"] is None
        else:
            assert attack["log2_cost"] == pytest.approx(time)


def test_excluding_all_algorithms_is_an_error():
    params = dict(n=15, m=17, q=2)
    params["excluded_algorithms"] = ce.MQEstimator(**params).algorithm_names()
    spec = InputSpec(kind="mq", label="empty", params=params)
    with pytest.raises(ValueError, match="No finite CryptographicEstimators attack"):
        route(spec).run(spec)


def test_non_prime_power_is_rejected_by_upstream():
    with pytest.raises(ValueError, match="prime power"):
        run_cryptographic_estimator("mq", dict(n=15, m=17, q=6))


def test_impossible_memory_bound_does_not_return_infeasible_attack():
    spec = InputSpec(kind="uov", label="bound", params=dict(n=24, m=10, q=2, memory_bound=0))
    with pytest.raises(ValueError, match="No finite CryptographicEstimators attack"):
        route(spec).run(spec)


def test_finite_memory_bound_selects_feasible_attack():
    spec = InputSpec(kind="uov", label="bound", params=dict(n=24, m=10, q=2, memory_bound=9))
    result = route(spec).run(spec)
    assert result.best_attack == "CollisionAttack"
    assert result.cost.log2_memory <= 9
