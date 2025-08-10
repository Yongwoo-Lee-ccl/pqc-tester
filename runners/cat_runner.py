
"""Runner for the CAT (code-based attack tool) CLI."""

import json
import os
import shlex
import subprocess
import tempfile

CAT_BIN = os.environ.get("CAT_BIN", "docker run --rm -v {tmp_dir}:/tmp pqc-tester-cat /tmp/{tmp_file}")


def run_cat(params: dict) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(params, f)
        tmp = f.name
        tmp_dir = os.path.dirname(tmp)
        tmp_file = os.path.basename(tmp)
    
    try:
        # Check if we're using Docker or direct binary
        if "docker" in CAT_BIN:
            # Use Docker with volume mounting
            cmd_str = CAT_BIN.format(tmp_dir=tmp_dir, tmp_file=tmp_file)
            cmd = shlex.split(cmd_str)
        else:
            # Use direct binary/script
            cmd = shlex.split(CAT_BIN) + [tmp]
        
        out = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    
    if out.returncode != 0:
        raise RuntimeError(out.stderr or out.stdout)
    return json.loads(out.stdout.strip() or "{}")
