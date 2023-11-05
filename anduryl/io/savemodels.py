from typing import Dict, List, Tuple
import numpy as np
from pydantic import BaseModel as PydanticBaseModel
from pydantic import field_validator
from anduryl import __version__


def underscore_to_space(string: str) -> str:
    return string.replace("_", " ")


class BaseModel(PydanticBaseModel):
    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        extra = "forbid"  # will throw errors so we can fix our models
        populate_by_name = True
        alias_generator = underscore_to_space


class Expert(BaseModel):
    name: str = ""
    user_weight: float = np.nan

    @field_validator("user_weight", mode='before')
    @classmethod
    def null_to_nan(cls, v):
        if v is None:
            return np.nan
        else:
            return v

class Item(BaseModel):
    realization: float = np.nan
    scale: str
    question: str = ""
    quantiles: List[float]
    unit: str = ""
    bounds: Tuple[float, float] = (np.nan, np.nan)
    overshoots: Tuple[float, float] = (np.nan, np.nan)

    @property
    def is_seed(self):
        return ~np.isnan(self.realization)

    @field_validator("scale")
    @classmethod
    def scale_must_by_uni_or_log(cls, v):
        if v.lower() not in ["uni", "log"]:
            raise ValueError(f'Scale must be "uni" or "log", got "{v}".')
        return v.lower()

    @field_validator("realization", mode='before')
    @classmethod
    def null_to_nan(cls, v):
        if v is None:
            return np.nan
        else:
            return v

    @field_validator("bounds", "overshoots", mode='before')
    @classmethod
    def tuple_null_to_nan(cls, v):
        return tuple(np.nan if item is None else item for item in v)

    # def realization_empty_string_to_nan(cls, v):
    #     if isinstance(v, str) and v.strip() == "":
    #         v = np.nan
    #     return v


class SaveModel(BaseModel):
    version: str = __version__
    experts: Dict[str, Expert] = {}
    items: Dict[str, Item] = {}
    assessments: Dict[str, Dict[str, list]] = {}
