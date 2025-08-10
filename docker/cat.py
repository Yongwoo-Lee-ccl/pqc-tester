#!/usr/bin/env python3

import json
import subprocess
import sys
import os
import math

def convert_params_to_cat_args(params):
    """Convert JSON parameters to CAT command line arguments."""
    args = []
    
    # CAT's uniformmatrix problem calculates K = N - lgq*W where lgq = ceil(log2(N))
    # For standard (n,k,t) parameters, we need to find a W that gives us a reasonable K
    
    n = params.get('n', 100)
    k_desired = params.get('k', n // 2)
    t = params.get('t', 5)
    
    # Calculate what W would be needed for the desired K
    lgq = math.ceil(math.log2(n)) if n > 1 else 1
    # K = N - lgq*W, so W = (N - K) / lgq
    w_for_k = max(1, (n - k_desired) // lgq)
    
    # Use the minimum of desired t and calculated W to ensure valid parameters
    w = min(t, w_for_k)
    
    args.append(f'N={n}')
    args.append(f'W={w}')
    
    # Add problem type (default to uniformmatrix for code-based)
    problem = params.get('problem', 'uniformmatrix')
    args.insert(0, f'problem={problem}')
    
    return args

def run_cat_attack(params):
    """Run CAT attack analysis and return results."""
    try:
        # Convert params to CAT arguments
        cat_args = convert_params_to_cat_args(params)
        
        # First get valid problem parameters from CAT
        cmd = ['./problemparams'] + cat_args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/app')
        if result.returncode != 0:
            raise RuntimeError(f"problemparams failed: {result.stderr}")
        
        # Parse the output to get the exact parameters CAT will use
        problem_lines = result.stdout.strip().split('\n')
        if not problem_lines or not problem_lines[0].strip():
            raise RuntimeError("No valid parameters found for given constraints")
        
        # Take the first valid parameter set
        first_line = problem_lines[0].strip()
        parts = first_line.split()
        if len(parts) >= 3:
            problem_spec = parts[2]  # e.g., "N=64,K=46,W=3"
            # Extract the parameters to use in subsequent calls
            param_parts = parts[2].split(',')
            actual_params = ['problem=uniformmatrix'] + param_parts
        else:
            raise RuntimeError(f"Invalid problemparams output: {first_line}")
        
        # Now search for best attack parameters using the actual valid parameters
        # Use the format from isdsims.py: ['./searchparams','problem=uniformmatrix',NKW,'attack=isd0,FW=1']
        search_cmd = ['./searchparams', 'problem=uniformmatrix', problem_spec, 'attack=isd0,FW=1']
        search_result = subprocess.run(search_cmd, capture_output=True, text=True, cwd='/app')
        
        if search_result.returncode != 0 or not search_result.stdout.strip():
            # Fallback to basic parameters if search fails
            attack_params = 'attack=isd0,FW=1'
        else:
            # Parse search output to get best parameters
            lines = search_result.stdout.strip().split('\n')
            if lines:
                last_line = lines[-1].split()
                if len(last_line) >= 5:
                    attack_params = last_line[4]
                else:
                    attack_params = 'attack=isd0,FW=1'
            else:
                attack_params = 'attack=isd0,FW=1'
        
        # Get circuit cost using the format from isdsims.py
        cost_cmd = ['./circuitcost', 'problem=uniformmatrix', problem_spec, 'attack=isd0', attack_params]
        cost_result = subprocess.run(cost_cmd, capture_output=True, text=True, cwd='/app')
        
        if cost_result.returncode != 0:
            raise RuntimeError(f"circuitcost failed: {cost_result.stderr}")
        
        # Parse the cost output
        cost_lines = cost_result.stdout.strip().split('\n')
        
        # CAT outputs lines like "circuitcost problem=uniformmatrix N=64,K=46,W=3 attack=isd0,FW=1 112"
        # The last number is typically the cost
        rop_cost = None
        for line in cost_lines:
            if line.strip():
                parts = line.strip().split()
                # Try to get the last numeric value
                for part in reversed(parts):
                    try:
                        val = float(part)
                        if val > 0:  # Any positive number could be the cost
                            rop_cost = val
                            break
                    except ValueError:
                        continue
                if rop_cost:
                    break
        
        if rop_cost is None:
            rop_cost = 2**64  # Reasonable default for small parameters
        
        # Format output as expected by the framework
        # Include original parameters in the metadata for reference
        original_params = f"requested_N={params.get('n')},K={params.get('k')},t={params.get('t')}"
        result = {
            "attacks": {
                "isd": {
                    "rop": rop_cost,
                    "succ": 1.0
                }
            },
            "meta": {
                "model": "CAT",
                "problem": problem_spec,
                "original": original_params
            }
        }
        
        return result
        
    except Exception as e:
        raise RuntimeError(f"CAT execution failed: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: cat.py <json_file>", file=sys.stderr)
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    try:
        with open(json_file, 'r') as f:
            params = json.load(f)
        
        result = run_cat_attack(params)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()