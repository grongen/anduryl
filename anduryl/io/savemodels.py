from typing import Dict, List, Tuple
import numpy as np
from pydantic import BaseModel as PydanticBaseModel
from pydantic import validator
from anduryl import __version__


def underscore_to_space(string: str) -> str:
    return string.replace("_", " ")


class BaseModel(PydanticBaseModel):
    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        extra = "forbid"  # will throw errors so we can fix our models
        allow_population_by_field_name = True
        alias_generator = underscore_to_space


class Expert(BaseModel):
    name: str = ""
    user_weight: float = np.nan


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

    @validator("scale")
    def scale_must_by_uni_or_log(cls, v):
        if v.lower() not in ["uni", "log"]:
            raise ValueError(f'Scale must be "uni" or "log", got "{v}".')
        return v.lower()

    # @validator("realization")
    # def realization_empty_string_to_nan(cls, v):
    #     if isinstance(v, str) and v.strip() == "":
    #         v = np.nan
    #     return v


class SaveModel(BaseModel):
    version: str = __version__
    experts: Dict[str, Expert] = {}
    items: Dict[str, Item] = {}
    assessments: Dict[str, Dict[str, list]] = {}
