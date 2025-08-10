# pqc-tester

A single front-end that routes one input spec to either
- **CAT** (code-based crypto attack analysis), or
- **lattice-estimator** (lattice/LWE/RLWE/MLWE).

It normalizes outputs into a common schema (`log2_cost`, `success_prob`, etc.).

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

The CLI prints a normalized JSON with the best attack and `log2_cost`.

## Environment

- Python 3.10+
- For lattice back-end: SageMath + `vendors/lattice-estimator`
- For code-based back-end: CAT with Docker (recommended) or manual install
- Docker (recommended for CAT to avoid complex dependencies)

## How CAT Works

**CAT (Cryptographic Attack Tester)** is a tool by Daniel J. Bernstein for analyzing code-based cryptosystem security. Here's how our integration works:

### Parameter Constraints
CAT has specific constraints on code parameters:
- **Input**: You provide `(n, k, t)` where n=code length, k=info length, t=error weight  
- **CAT's internal logic**: Uses `(N, K, W)` where `K = N - ceil(log2(N)) * W`
- **Mapping**: Our wrapper maps your `t → W` and lets CAT calculate its own `K`

### Attack Flow
1. **`problemparams`**: CAT finds valid `(N,K,W)` combinations for your `N` and `W`
2. **`searchparams`**: CAT optimizes attack parameters for ISD (Information Set Decoding)  
3. **`circuitcost`**: CAT estimates the circuit complexity (in ROPs - Random Oracle Primes)

### Example
```bash
Input: {"n": 64, "k": 32, "t": 3}
CAT uses: N=64, K=46, W=3  # K calculated by CAT's formula
Output: ~12,090 ROPs (2^13.6 complexity)
```

### Limitations
- CAT only supports specific code families (uniformmatrix problem)
- Your desired `k` may differ from CAT's calculated `K` due to constraints
- CAT is optimized for research scenarios, not arbitrary parameter sets

## Roadmap

- Proper MLWE→LWE mapping with exact Kyber noise parameters
- Richer attack set selection and model flags  
- Support for more flexible code parameters in CAT
- Additional code-based cryptosystem families
