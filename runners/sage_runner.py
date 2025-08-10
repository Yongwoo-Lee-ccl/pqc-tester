import subprocess, json, tempfile, os, textwrap

SAGE = os.environ.get("SAGE_BIN", "sage")
EST_PATH = os.path.abspath(os.environ.get("LATTICE_ESTIMATOR_PATH", "vendors/lattice-estimator"))

def _mlwe_to_lwe(params: dict):
    n = int(params.get("n", 256))
    k = int(params.get("module_k", 2) or 1)
    q = int(params.get("q", 3329))

    def parse_noise(noise_params):
        if "type" in noise_params:
            if noise_params["type"] == "CenteredBinomial":
                return f"ND.CenteredBinomial({noise_params['eta']})"
            elif noise_params["type"] == "UniformMod":
                return f"ND.UniformMod({noise_params['q_noise']})"
        # Fallback for old format
        return f"ND.CenteredBinomial({noise_params.get('eta', 2)})"


    if "Xs" in params and isinstance(params["Xs"], dict):
        Xs_str = parse_noise(params["Xs"])
        Xe_str = parse_noise(params["Xe"])
    else: # old format
        eta1 = int(params.get("eta1", 3))
        eta2 = int(params.get("eta2", 2))
        Xs_str = f"ND.CenteredBinomial({eta1})"
        Xe_str = f"ND.CenteredBinomial({eta2})"


    return {"n": n*k, "q": q, "Xs_str": Xs_str, "Xe_str": Xe_str}

def run_estimator(params: dict) -> dict:
    problem = (params.get("problem") or "RLWE").upper()
    if problem in ("RLWE","MLWE"):
        lwe = _mlwe_to_lwe(params)
        lwe_params_str = f"LWE.Parameters(n={lwe['n']}, q={lwe['q']}, Xs={lwe['Xs_str']}, Xe={lwe['Xe_str']})"
    elif problem == "NTRU":
        n = int(params.get("n", 512))
        q = int(params.get("q", 12289))
        
        # Check if this is Falcon (NTRU-based signature)
        if params.get("scheme_name") == "falcon":
            sigma = float(params.get("sigma", 1.17))  # Falcon's signature standard deviation
            lwe_params_str = f"LWE.Parameters(n={n}, q={q}, Xs=ND.DiscreteGaussian({sigma}), Xe=ND.DiscreteGaussian({sigma}))"
        else:
            # Standard NTRU with ternary secrets
            lwe_params_str = f"LWE.Parameters(n={n}, q={q}, Xs=ND.UniformMod(3), Xe=ND.UniformMod(3))"
    else:
        lwe = {"n": int(params["n"]), "q": int(params["q"]), "alpha": float(params.get("alpha", 0.005))}
        lwe_params_str = f"LWE.Parameters(n={lwe['n']}, q={lwe['q']}, Xs=ND.DiscreteGaussianAlpha({lwe['alpha']}, {lwe['q']}), Xe=ND.DiscreteGaussianAlpha({lwe['alpha']}, {lwe['q']}))"


    code = textwrap.dedent(f"""
    import sys
    sys.path.append("{EST_PATH}")
    import json
    from estimator import LWE
    from estimator import nd as ND

    lwe_params = {lwe_params_str}

    # Compare a few standard attacks (names may differ by estimator version)
    results = {{}}
    try:
        res_primal = LWE.primal_usvp(lwe_params)
        results["primal_usvp"] = {{"rop": float(res_primal.get("rop", 0.0))}}
    except Exception as e:
        results["primal_usvp"] = {{"error": str(e)}}
    try:
        res_dual = LWE.dual(lwe_params)
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