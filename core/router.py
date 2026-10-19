
from .models import InputSpec
from adapters.cat_adapter import CatAdapter
from adapters.lattice_adapter import LatticeAdapter
from adapters.cryptographic_adapter import CryptographicAdapter

def route(spec: InputSpec):
    if spec.kind == "code":
        return CatAdapter()
    elif spec.kind == "lattice":
        return LatticeAdapter()
    elif spec.kind in ("mq", "uov", "mayo"):
        return CryptographicAdapter()
    else:
        raise ValueError(f"Unknown kind: {spec.kind}")
