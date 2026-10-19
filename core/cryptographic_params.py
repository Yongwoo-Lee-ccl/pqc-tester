"""JSON-safe inputs for the supported CryptographicEstimators families."""

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CryptographicParams(BaseModel):
    # Upstream accepts **kwargs; reject typos instead of silently ignoring them.
    model_config = ConfigDict(extra="forbid")

    n: int = Field(gt=0, strict=True)
    m: int = Field(gt=0, strict=True)
    q: int = Field(ge=2, strict=True)
    w: float = Field(default=2.81, ge=2, le=3, allow_inf_nan=False)
    theta: float | None = Field(default=2, ge=0, le=2, allow_inf_nan=False)
    memory_bound: float = Field(default=math.inf, ge=0, allow_inf_nan=False)
    memory_access: Literal[0, 1, 2, 3] = 0
    bit_complexities: Literal[0, 1] = 1
    excluded_algorithms: list[str] = Field(default_factory=list)


class MQParams(CryptographicParams):
    nsolutions: float = Field(default=0, ge=0, allow_inf_nan=False)


class UOVParams(CryptographicParams):
    cost_one_hash: float = Field(default=17.5, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_dimensions(self):
        if self.n <= self.m:
            raise ValueError("UOV requires n > m (n is total variables, m is oil variables)")
        return self


class MAYOParams(CryptographicParams):
    o: int = Field(gt=0, strict=True)
    k: int = Field(gt=0, strict=True)
    theta: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    cost_one_hash: float = Field(default=17, ge=0, allow_inf_nan=False)
    w_ks: float = Field(default=2.8, ge=2, le=3, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_dimensions(self):
        if self.n <= self.m:
            raise ValueError("MAYO requires n > m")
        if self.k >= self.n - self.o:
            raise ValueError("MAYO requires k < n - o")
        return self


PARAM_MODELS = {"mq": MQParams, "uov": UOVParams, "mayo": MAYOParams}
