
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any

SchemeKind = Literal["code", "lattice"]

class CodeParams(BaseModel):
    n: int
    k: Optional[int] = None
    t: Optional[int] = None
    code_family: Optional[str] = None
    error_model: Optional[str] = None

class LatticeParams(BaseModel):
    problem: Literal["LWE","RLWE","NTRU","SIS","MLWE"] = "RLWE"
    n: int
    q: int
    alpha: Optional[float] = None
    ring: Optional[bool] = None
    cyclo: Optional[int] = None
    module_k: Optional[int] = None
    eta1: Optional[int] = None
    eta2: Optional[int] = None
    du: Optional[int] = None
    dv: Optional[int] = None

class InputSpec(BaseModel):
    kind: SchemeKind
    label: str
    params: Dict[str, Any]

class AttackCost(BaseModel):
    rops: float
    log2_cost: float
    mem_bytes: Optional[int] = None
    success_prob: Optional[float] = None
    time_model: Optional[str] = None

class Result(BaseModel):
    kind: SchemeKind
    label: str
    best_attack: str
    cost: AttackCost
    details: Dict[str, Any]
    notes: Optional[str] = None
