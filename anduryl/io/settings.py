from pydantic import confloat
from typing import Tuple, Union
from pathlib import Path

from pydantic import BaseModel as PydanticBaseModel


class BaseModel(PydanticBaseModel):
    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
        # use_enum_values = True
        extra = "forbid"  # will throw errors so we can fix our models
        # allow_population_by_field_name = True
        # alias_generator = to_key


class SaveFigureSettings(BaseModel):

    figure_type: str
    figure_selection: Union[str, None]
    title_option: str
    title_line_characters: int
    save_path_overview: Path
    save_directory_single_figures: Path
    figure_extension: str
    figsize_horizontal: float
    figsize_vertical: float
    figure_dpi: int
    n_axes_cols: int = None
    n_axes_rows: int = None
    add_legend: bool
    legend_position: str
    legend_anchor: Tuple[Union[float, None], Union[float, None]]

    # @validator("figure_extension")
    # def path_parent_exists(cls, v):
    #     if not v:
    #         raise ValueError("No extension was given")

    #     return v


# class SaveOverviewFigureSettings(BaseModel):

#     main_option: str
#     title_option: str
#     title_line_characters: int
#     figure_path: Path
#     figsize_horizontal: float
#     figsize_vertical: float
#     n_axes_cols: int
#     n_axes_rows: int
#     figure_dpi: int
#     legend_position: str
#     legend_anchor: Tuple[float, float] = None

#     @validator("figure_path")
#     def path_parent_exists(cls, v):
#         if not v.name:
#             raise OSError(f"No file name was given to save figure to.")
#         if not v.parent.exists():
#             raise OSError(f'Directory to save figure "{v.parent}" does not exists.')
#         return v


class CalculationSettings(BaseModel):
    id: str  # = "DM"
    name: str  # = "Decision Maker"
    weight: str  # = "Global"
    overshoot: confloat(ge=0.0)  # = 0.1
    alpha: Union[confloat(ge=0.0), None]  # = 0.0
    optimisation: bool  # = True
    robustness: bool  # = True
    calpower: confloat(ge=0.0)  # = 1.0
