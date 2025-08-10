
"""Runner for the CAT (code-based attack tool) CLI."""

import json
import os
import shlex
import subprocess
import tempfile

CAT_BIN = os.environ.get("CAT_BIN", "python3 vendors/cat/cat.py")


def run_cat(params: dict) -> dict:
    cmd = shlex.split(CAT_BIN)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(params, f)
        tmp = f.name
    try:
        out = subprocess.run(cmd + [tmp], capture_output=True, text=True)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    if out.returncode != 0:
        raise RuntimeError(out.stderr or out.stdout)
    return json.loads(out.stdout.strip() or "{}")
