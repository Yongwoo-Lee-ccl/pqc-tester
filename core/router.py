
from .models import InputSpec
from adapters.cat_adapter import CatAdapter
from adapters.lattice_adapter import LatticeAdapter

def route(spec: InputSpec):
    if spec.kind == "code":
        return CatAdapter()
    elif spec.kind == "lattice":
        return LatticeAdapter()
    else:
        raise ValueError(f"Unknown kind: {spec.kind}")
