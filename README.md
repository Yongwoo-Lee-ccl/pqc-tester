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

# Test the Docker image
echo '{"n": 100, "k": 50, "t": 10}' | docker run --rm -i pqc-tester-cat /dev/stdin
```

**Alternative: Manual Installation**
Download and install CAT from https://cat.cr.yp.to/software.html:

**On Ubuntu/Debian:**
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install build-essential libgmp-dev python3-dev

# Download and build CAT
# Visit https://cat.cr.yp.to/software.html to download the latest version
tar -xzf cryptattacktester-YYYYMMDD.tar.gz
cd cryptattacktester-YYYYMMDD
make
cd ..
mv cryptattacktester-YYYYMMDD vendors/cat

# Set environment variable to use local installation
export CAT_BIN="python3 vendors/cat/cat.py"
```

**On macOS:**
```bash
# Install dependencies via Homebrew
brew install gmp

# Then follow the Ubuntu build steps above
# Note: May require additional configuration for GMP paths
```

By default, the framework uses Docker. Set `CAT_BIN` environment variable to override.

#### Lattice Estimator
```bash
git submodule add https://github.com/malb/lattice-estimator vendors/lattice-estimator
git submodule update --init --recursive
```

`runners/sage_runner.py` expects `sage` in PATH and `LATTICE_ESTIMATOR_PATH` pointing to `vendors/lattice-estimator` (default already points there).

## Presets

- `presets/kyber512.json` — Kyber-512 (128-bit security target). Routed to lattice estimator (as MLWE, crudely mapped to LWE for now).
- `presets/hqc128.json` — HQC-128. Routed to CAT.
- `presets/mceliece348864.json` — Classic McEliece 348864. Routed to CAT.

## Usage

```bash
python cli.py presets/kyber512.json
python cli.py presets/hqc128.json
python cli.py presets/mceliece348864.json
```

The CLI prints a normalized JSON with the best attack and `log2_cost`.

## Environment

- Python 3.10+
- For lattice back-end: SageMath + `vendors/lattice-estimator`
- For code-based back-end: CAT (`CAT_BIN` may override the CLI path; defaults to `vendors/cat/cat.py`).

## Roadmap

- Proper MLWE→LWE mapping with exact Kyber noise parameters.
- Richer attack set selection and model flags.
- Dockerized runners for strict reproducibility.
