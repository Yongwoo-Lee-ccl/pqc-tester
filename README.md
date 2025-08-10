
# sec-framework

A single front-end that routes one input spec to either
- **CAT** (code-based crypto attack analysis), or
- **lattice-estimator** (lattice/LWE/RLWE/MLWE).

It normalizes outputs into a common schema (`log2_cost`, `success_prob`, etc.).

## Layout

```
sec-framework/
  adapters/               # Adapters for each backend
  core/                   # Shared models, router, normalizers
  runners/                # External tool runners
  vendors/                # Place submodules here
  presets/                # Ready-to-run example specs
  cli.py                  # CLI entry
```

## Install

```bash
pip install -e .
```

### Bring the vendors (as submodules)

```bash
git submodule add https://cat.cr.yp.to vendors/cat
git submodule add https://github.com/malb/lattice-estimator vendors/lattice-estimator
git submodule update --init --recursive
```

> Note: CAT integration code (`runners/cat_runner.py`) is a placeholder. Replace with CAT's actual CLI invocation and parsing logic when available.
> `runners/sage_runner.py` expects `sage` in PATH and `LATTICE_ESTIMATOR_PATH` pointing to `vendors/lattice-estimator` (default already points there).

## Presets

- `presets/kyber512.json` — Kyber-512 (128-bit security target). Routed to lattice estimator (as MLWE, crudely mapped to LWE for now).
- `presets/hqc128.json` — HQC-128. Routed to CAT (placeholder behavior in current mock).

## Usage

```bash
python cli.py presets/kyber512.json
python cli.py presets/hqc128.json
```

The CLI prints a normalized JSON with the best attack and `log2_cost`.

## Environment

- Python 3.10+
- For lattice back-end: SageMath + `vendors/lattice-estimator`
- For code-based back-end: CAT. Update `runners/cat_runner.py` to actually call CAT.

## Roadmap

- Proper MLWE→LWE mapping with exact Kyber noise parameters.
- Richer attack set selection and model flags.
- Dockerized runners for strict reproducibility.
- CAT real runner implementation and output parser.
