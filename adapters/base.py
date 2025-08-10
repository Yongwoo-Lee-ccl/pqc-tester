
from abc import ABC, abstractmethod
from core.models import InputSpec, Result

class Adapter(ABC):
    @abstractmethod
    def run(self, spec: InputSpec) -> Result:
        ...
