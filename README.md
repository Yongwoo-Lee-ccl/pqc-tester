# pqc-tester

A single front-end that routes one input spec to either
- **CAT** (code-based crypto attack analysis), or
- **lattice-estimator** (lattice/LWE/RLWE/MLWE).

It normalizes outputs into a common schema (`log2_cost`, `success_prob`, etc.).

## ⚠️ Disclaimer

**This code was co-generated with AI tools and may contain errors.** While the implementation has been tested with various parameter sets, users should:
- **Verify results independently** for critical security assessments
- **Cross-reference with original tools** (CAT, lattice-estimator) when needed
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

#### CAT (Code Attack Tool)

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

#### Lattice Estimator
```bash
git submodule add https://github.com/malb/lattice-estimator vendors/lattice-estimator
git submodule update --init --recursive
```

`runners/sage_runner.py` expects `sage` in PATH and `LATTICE_ESTIMATOR_PATH` pointing to `vendors/lattice-estimator` (default already points there).

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
- Docker (recommended for CAT to avoid complex dependencies)

## How CAT Works

**CAT (Cryptographic Attack Tester)** is a tool by Daniel J. Bernstein for analyzing code-based cryptosystem security. Here's how our integration works:

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
- **Attack scope**: Focuses on ISD variants; does not cover all possible code-breaking approaches
- **Classical security**: Provides classical complexity estimates; quantum impact requires separate analysis

**Academic References**: 
- **CAT (Code-based cryptanalysis)**: Bernstein, D.J. "cryptattacktester software" (2023). https://cat.cr.yp.to/
- **Section 4.6 parameter constraints** are documented in the CAT technical specifications
- The underlying ISD algorithms and complexity analysis are described in the CAT documentation and related papers on code-based cryptanalysis available at https://cat.cr.yp.to/papers.html
- **Lattice Estimator (Lattice-based cryptanalysis)**: Albrecht, M.R., Player, R., and Scott, S. "On the concrete hardness of Learning with Errors" (2015). Available at https://github.com/malb/lattice-estimator

## Roadmap

- Proper MLWE→LWE mapping with exact Kyber noise parameters
- Richer attack set selection and model flags  
- Support for more flexible code parameters in CAT
- Additional code-based cryptosystem families
