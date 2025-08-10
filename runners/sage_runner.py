
import subprocess, json, tempfile, os, textwrap

SAGE = os.environ.get("SAGE_BIN", "sage")
EST_PATH = os.environ.get("LATTICE_ESTIMATOR_PATH", "vendors/lattice-estimator")

def _mlwe_to_lwe(params: dict):
    # very light mapping for Kyber-like presets (for demonstration)
    n = int(params.get("n", 256))
    k = int(params.get("module_k", 2) or 1)
    q = int(params.get("q", 3329))
    # crude alpha from eta1 (NOT exact; placeholder to be refined)
    eta1 = int(params.get("eta1", 3))
    alpha = float(params.get("alpha", 0.0015 if eta1==3 else 0.002))
    return {"n": n*k, "q": q, "alpha": alpha}

def run_estimator(params: dict) -> dict:
    # Decide path: LWE/RLWE/MLWE
    problem = (params.get("problem") or "RLWE").upper()
    if problem in ("RLWE","MLWE"):
        lwe = _mlwe_to_lwe(params)
    else:
        lwe = {"n": int(params["n"]), "q": int(params["q"]), "alpha": float(params.get("alpha", 0.005))}

    code = textwrap.dedent(f"""
    load("{EST_PATH}/estimator.py")  # modern entry, falls back if needed
    import json
    from estimator import LWE, attacks

    lwe = LWE.Parameters(n={lwe["n"]}, q={lwe["q"]}, alpha={lwe["alpha"]})

    # Compare a few standard attacks (names may differ by estimator version)
    results = {{}}
    try:
        res_primal = attacks.primal_usvp(lwe)
        results["primal_usvp"] = {{"rop": float(res_primal.get("rop", 0.0))}}
    except Exception as e:
        results["primal_usvp"] = {{"error": str(e)}}
    try:
        res_dual = attacks.dual(lwe)
        results["dual"] = {{"rop": float(res_dual.get("rop", 0.0))}}
    except Exception as e:
        results["dual"] = {{"error": str(e)}}

    print(json.dumps({{"attacks": results, "meta": {{"mapped_from": "{problem}"}}}}))
    """)

    with tempfile.NamedTemporaryFile("w", suffix=".sage", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        out = subprocess.run([SAGE, tmp], capture_output=True, text=True, check=False)
    finally:
        try: os.unlink(tmp)
        except Exception: pass

    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout.strip() or "{}")
