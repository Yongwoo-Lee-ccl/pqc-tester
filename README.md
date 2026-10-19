# pqc-tester

A single front-end that routes one input spec to
- **CAT** (code-based crypto attack analysis),
- **lattice-estimator** (lattice/LWE/RLWE/MLWE), or
- **CryptographicEstimators** (MQ problems and UOV/MAYO signatures).

It normalizes outputs into a common schema (`log2_cost`, `success_prob`, etc.).

## ⚠️ Disclaimer

**This code was co-generated with AI tools and may contain errors.** While the implementation has been tested with various parameter sets, users should:
- **Verify results independently** for critical security assessments
- **Cross-reference with original tools** (CAT, lattice-estimator, CryptographicEstimators) when needed
- **Report issues** if discrepancies are found between this wrapper and the underlying tools
- **Use with caution** in production security evaluations

The academic references and mathematical formulations should be considered authoritative over this implementation.

## Layout

```
pqc-tester/
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

### Bring the vendors

#### 1. Lattice Estimator
```bash
git submodule add https://github.com/malb/lattice-estimator vendors/lattice-estimator
git submodule update --init --recursive
```

`runners/sage_runner.py` expects `sage` in PATH and `LATTICE_ESTIMATOR_PATH` pointing to `vendors/lattice-estimator` (default already points there).


#### 2. CAT (CryptAttackTester)

**Recommended: Docker Setup (Easiest)**
```bash
# Build the CAT Docker image
docker build -f docker/Dockerfile.cat -t pqc-tester-cat .

# Test the Docker image with a small example
echo '{"n": 64, "k": 32, "t": 3}' > /tmp/test.json
docker run --rm -v /tmp:/tmp pqc-tester-cat /tmp/test.json
```

**Alternative: Manual Installation**
Download and install CAT from https://cat.cr.yp.to/software.html:

**On Ubuntu/Debian:**
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install build-essential libgmp-dev libmpfi-dev libssl-dev python3-dev

# Download and build CAT
wget https://cat.cr.yp.to/cryptattacktester-20231020.tar.gz
tar -xzf cryptattacktester-20231020.tar.gz
cd cryptattacktester-20231020
make -j4
make lib.so
cd ..
mv cryptattacktester-20231020 vendors/cat

# Copy the wrapper script
cp docker/cat.py vendors/cat/cat.py

# Set environment variable to use local installation
export CAT_BIN="python3 vendors/cat/cat.py"
```

**On macOS:**
```bash
# Install dependencies via Homebrew
brew install gmp mpfi

# Then follow the Ubuntu build steps above
# Note: May require additional configuration for library paths
```

By default, the framework uses Docker. Set `CAT_BIN` environment variable to override.

#### 3. CryptographicEstimators (MQ, UOV, MAYO)

Install the optional backend from the repository root:

```bash
pip install -e '.[crypto-estimators]'
python cli.py presets/mq-small.json
python cli.py presets/uov-small.json
python cli.py presets/mayo-small.json
# The installed entry point accepts the same spec files:
sec-estimate presets/uov-small.json
```

This uses the local [CryptographicEstimators Python library](https://github.com/Crypto-TII/CryptographicEstimators),
pinned to the tested version **2.1.1**. It requires neither SageMath nor Docker
and does not send specs to the [web application](https://estimators.crypto.tii.ae/).
The backend is imported only when an MQ/UOV/MAYO spec is run; the base install
continues to support CAT and lattice-estimator without it.

Use the existing `{kind, label, params}` input format:

```json
{
  "kind": "uov",
  "label": "Toy UOV example",
  "params": {"n": 24, "m": 10, "q": 2}
}
```

| `kind` | Required `params` | Interpretation |
| --- | --- | --- |
| `mq` | `n`, `m`, `q` | Number of variables, quadratic equations, field order |
| `uov` | `n`, `m`, `q` | Total variables, oil variables/equations, field order; `n > m` |
| `mayo` | `n`, `m`, `q`, `o`, `k` | Total variables, equations, field order, oil dimension, whipping parameter; `n > m`, `0 < k < n - o` |

Dimensions must be positive JSON integers and `q` must be a prime power.
Unknown keys and invalid options are rejected. Optional keys in `params`:

| Key | Meaning |
| --- | --- |
| `w` | Linear algebra exponent in `[2, 3]`; upstream default 2.81 |
| `theta` | Bit-conversion exponent in `[0, 2]`, or `null` for the upstream quadratic conversion; upstream defaults: MQ/UOV 2, MAYO `null` |
| `bit_complexities` | `1` (default) for bit operations/bits, `0` for field operations/elements |
| `memory_access` | `0` (constant, default), `1` (logarithmic), `2` (square root), `3` (cube root) |
| `memory_bound` | Nonnegative log₂ memory limit in the chosen memory unit; omitted means unlimited |
| `excluded_algorithms` | List of case-sensitive upstream class names, e.g. `["Crossbred"]` for MQ or `["WedgeAttack"]` for UOV/MAYO; unknown names are rejected |
| `nsolutions` | MQ only: log₂ solution count; omitted uses the upstream expected solution count |
| `cost_one_hash` | UOV/MAYO only: log₂ bit cost of one hash; upstream defaults 17.5 / 17 |
| `w_ks` | MAYO only: Kipnis–Shamir linear algebra exponent; upstream default 2.8 |

Only classical concrete estimates are normalized. Asymptotic/quantum options
and other CryptographicEstimators families are not exposed by this adapter.
See the [upstream user guide](https://github.com/Crypto-TII/CryptographicEstimators/blob/v2.1.1/docs/github/user_guide.md)
for the underlying cost models. Larger inputs can require substantial optimization time.

The result selects the smallest finite time among successful attacks satisfying
the memory limit. For UOV/MAYO this compares both forgery and key recovery;
`details.attacks.<name>.attack_type` retains that distinction. Each attack also
records `log2_cost`, `log2_memory`, and optimal `parameters`; unavailable costs
are `null`, and failed attacks retain an `error`. An empty feasible set is an error.

`cost.log2_cost` is the upstream time logarithm, and `cost.log2_memory` is the
upstream memory logarithm. `details.meta` records the backend version, input
parameters, memory bound, and time/memory units. With bit complexities enabled,
`cost.mem_bytes` is `ceil(2**log2_memory / 8)` when representable; with field
complexities it is `null`. `cost.rops` expands the time logarithm into the
selected operation unit and is `null` on float overflow/underflow; the logarithm
remains available. The backend does not supply a common success probability,
so `success_prob` is `null`. These cost models should not be directly equated
with CAT circuit counts or lattice-estimator operation counts.

## Presets

### Code-based Schemes (routed to CAT)
- `presets/test-tiny.json` — Small test case: (64,32,3) for fast testing
- `presets/test-small.json` — Small test case: (100,50,4) for fast testing  
- `presets/bike-l1.json` — BIKE Level 1 parameters
- `presets/hqc128.json` — HQC-128
- `presets/mceliece348864.json` — Classic McEliece 348864
- `presets/lightsaber.json` — Lightsaber parameters
- `presets/saber.json` — Saber parameters
- `presets/firesaber.json` — FireSaber parameters

### Lattice-based Schemes (routed to lattice-estimator)  
- `presets/kyber512.json` — Kyber-512 (128-bit security target)
- `presets/kyber768.json` — Kyber-768 (192-bit security target)
- `presets/kyber1024.json` — Kyber-1024 (256-bit security target)
- `presets/dilithium2.json` — Dilithium2
- `presets/falcon512.json` — Falcon-512
- `presets/falcon1024.json` — Falcon-1024

### Multivariate examples (routed to CryptographicEstimators)

- `presets/mq-small.json` — MQ with 15 variables, 17 equations over GF(2)
- `presets/uov-small.json` — UOV with 24 total variables, 10 oil variables over GF(2)
- `presets/mayo-small.json` — MAYO with `(n,m,o,k,q) = (16,12,4,2,16)`

These are small execution examples, **not secure parameter sets or security recommendations**.

## Usage

```bash
# Test with small/fast examples first
python cli.py presets/test-tiny.json
python cli.py presets/test-small.json

# Run actual cryptographic parameter sets
python cli.py presets/kyber512.json
python cli.py presets/hqc128.json
python cli.py presets/bike-l1.json
```

### Parameter Validation
The CLI automatically validates code-based parameters against **section 4.6 constraints** and warns about potential issues:

```bash
# Example with parameters that violate section 4.6 constraints
echo '{"kind": "code", "label": "Test", "params": {"n": 64, "k": 32, "t": 3}}' > test.json
python cli.py test.json

# Output includes section 4.6 validation warnings:
# ⚠️  Warning: k=32 violates CAT rate constraint 0.7n ≤ k ≤ 0.8n
#    Required range: 44.8 ≤ k ≤ 51.2
# ⚠️  Warning: k=32 doesn't match CAT's structural constraint  
#    CAT formula: k = n - t⌈log₂(n)⌉ = 64 - 3×6 = 46
#    CAT will use k=46 instead of your requested k=32
```

The CLI prints a normalized JSON with the best attack, `log2_cost`, and metadata about parameter adjustments.

## Environment

- Python 3.10+
- For lattice back-end: SageMath + `vendors/lattice-estimator`
- For code-based back-end: CAT with Docker (recommended) or manual install
- For MQ/UOV/MAYO: optional `crypto-estimators` extra (CryptographicEstimators 2.1.1)
- Docker (recommended for CAT to avoid complex dependencies)

## Tests

```bash
pip install -e '.[dev,crypto-estimators]'
python -m pytest -q
```

Tests cover routing, validation, unavailable algorithms, cost units, large
logarithms, memory bounds, and CLI results compared with the upstream
`estimate()` API for all three multivariate presets. Without the optional
backend, integration tests are skipped and wrapper tests still run. CI tests
both installation modes on Python 3.10 and 3.12. CAT/SageMath execution requires
their separate environments and is not part of this test suite.

## How CAT Works

**CAT (Cryptographic Attack Tester)** is a tool by Bernstein and Chou for analyzing code-based cryptosystem security. Here's how our integration works:

### Parameter Constraints & Limitations

CAT has specific mathematical constraints on code parameters as documented in **section 4.6** of the CAT paper:

**Section 4.6 Constraints:**
1. **Size constraint**: `n ≥ 8`
2. **Rate constraint**: `0.7n ≤ k ≤ 0.8n` 
3. **Structural constraint**: `k = n - t⌈log₂(n)⌉`

**How this affects your input:**
- **Input**: You provide `(n, k, t)` where n=code length, k=info length, t=error weight  
- **CAT's behavior**: Uses your `n` and `t`, but calculates `K = n - t⌈log₂(n)⌉`
- **Validation**: CLI checks all three constraints and warns about violations
- **Mapping**: Our wrapper maps `t → W` and lets CAT enforce its constraints

**Important**: Your desired `k` may differ significantly from CAT's calculated `K` due to section 4.6 constraints. The CLI will warn you when parameters will be adjusted.

### Attack Flow
1. **`problemparams`**: CAT finds valid `(N,K,W)` combinations for your `N` and `W`
2. **`searchparams`**: CAT optimizes parameters for each ISD variant (ISD0, ISD1, ISD2)  
3. **`circuitcost`**: CAT estimates circuit complexity for each attack
4. **Best selection**: Our wrapper returns the attack with lowest cost (strongest attack)

### Example
```bash
Input: {"n": 64, "k": 32, "t": 3}
CAT tests: ISD0, ISD1, ISD2 variants with N=64, K=46, W=3
Best attack: ISD1 with ~6,034 ROPs (2^12.6 complexity)
Output includes: attack name, cost, and metadata about all variants tested
```

### Limitations
- **Code families**: CAT only supports the "uniformmatrix" problem type (random linear codes)
- **Parameter flexibility**: Your desired `k` may differ from CAT's calculated `K` due to rate constraints  
- **Research focus**: CAT is optimized for cryptanalytic research, not arbitrary parameter validation
- **Attack scope**: Focuses on ISD variants; does not cover all possible cryptanalysis approaches
- **Classical security**: Provides classical complexity estimates; quantum impact requires separate analysis

**References**: 
- **CAT (Code-based cryptanalysis)**: BDaniel J. Bernstein, Tung Chou. "CryptAttackTester: high-assurance attack analysis." Crypto 2024.
- **Lattice Estimator (Lattice-based cryptanalysis)**: Albrecht, M.R., Player, R., and Scott, S. "On the concrete hardness of Learning with Errors" (2015). Available at https://github.com/malb/lattice-estimator

## Roadmap

- Proper MLWE→LWE mapping with exact Kyber noise parameters
- Richer attack set selection and model flags  
- Support for more flexible code parameters in CAT
- Additional code-based cryptosystem families
