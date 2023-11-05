import re
from pathlib import Path
from typing import Union
from io import StringIO

import numpy as np
from anduryl.io import reader, writer
from anduryl.io.savemodels import SaveModel
from anduryl.model.assessment import Assessment, ExpertAssessment


class ProjectIO:
    """
    IO class for anduryl project
    """

    def __init__(self, project) -> None:
        """
        Constructor

        Parameters
        ----------
        project : anduryl.main.Project
            Project class
        """
        self.project = project

    def to_file(self, path: Union[str, Path]) -> None:
        """
        Saves project to file, calls the save function dependend
        on the path extension

        Parameters
        ----------
        path : str
            Path to save file
        """
        if not isinstance(path, Path):
            path = Path(path)

        if path.suffix.lower() == ".dtt":
            self.to_excalibur(path)
        elif path.suffix.lower() == ".json":
            self.to_json(path)
        else:
            OSError(f'Suffix "{path.suffix}" not recognized. Expected ".dtt" or ".json".')

    def to_excalibur(self, dttfile: Union[str, Path]) -> None:
        """
        Save to Excalibur format

        Parameters
        ----------
        dttfile : str
            .dtt file for excalibur. .rls file is derived from the name by replacing the extension
        """
        if not isinstance(dttfile, Path):
            dttfile = Path(dttfile)

        # Get rls filename
        rlsfile = dttfile.parent / (dttfile.stem + ".rls")
        # Save
        writer.write_excalibur(self.project, dttfile, rlsfile)

    def to_savemodel(self) -> SaveModel:
        """Convert project data structure to savemodel structure. This
        can than be exported to a json file.

        Returns:
            SaveModel: File Structure that can be exported to JSON
        """

        project = self.project

        expert_data_T = list(zip(*[project.experts.names, project.experts.user_weights]))
        expert_data_T = [expert_data_T[i] for i in project.experts.actual_experts]

        # Create item dictionary
        item_dict = project.items.as_dict(
            orient="index",
            lists=["ids", "scales", "realizations", "questions", "units", "bounds", "overshoots"],
        )
        # Add quantiles to items
        quantiles = np.array(project.assessments.quantiles)
        for key, subdict in item_dict.items():
            subdict["quantiles"] = quantiles[
                project.items.use_quantiles[project.items.ids.index(key)]
            ].tolist()

        # Get assessment dict from array
        assessment_dict = writer.elements_to_dict(
            np.swapaxes(project.assessments.array, 1, 2)[project.experts.actual_experts],
            [project.experts.get_exp("actual"), project.items.ids, project.assessments.quantiles],
        )
        # Add estimates to list
        assessment_dict = {
            exp: {
                item: [itemdict[k] for k in item_dict[item]["quantiles"]]
                for item, itemdict in expdict.items()
            }
            for exp, expdict in assessment_dict.items()
        }

        # Create dictionary
        project_dct = {
            "experts": writer.elements_to_dict(
                expert_data_T, [project.experts.get_exp("actual"), ["name", "user_weight"]]
            ),
            "items": item_dict,
            "assessments": assessment_dict,
            # "results": {key: project.results[key].settings for key in project.results.keys()},
        }

        return SaveModel.model_validate(project_dct)

    def to_json(self, path: Union[str, Path]) -> None:
        """
        Save project to json

        Parameters
        ----------
        path : str
            Path to json file
        """
        if not isinstance(path, Path):
            path = Path(path)

        if not path.suffix.lower() == ".json":
            raise ValueError("Filename should end with .json")

        # Convert to savemodel
        savemodel = self.to_savemodel()

        # Save
        with path.open("w") as f:
            text = savemodel.model_dump_json(indent=4)
            # Remove line breaks inside lists (last level of json-file) to make the json easier to read
            for match in re.findall("\[[\s\S]*?\]", text):
                text = text.replace(match, "[" + " ".join(match[1:-1].split()) + "]")

            f.write(text)

    def load_file(self, path: Union[str, Path]) -> None:
        """
        Loads file given a file name. The load function of
        excalbur or json is called based on the extension.

        Parameters
        ----------
        path : str
            Path to file
        """
        if not isinstance(path, Path):
            path = Path(path)

        if path.suffix.lower() == ".dtt":
            # Load project
            rlsfile = path.parent / (path.stem + ".rls")
            if rlsfile.exists():
                self.load_excalibur(path, rlsfile)
            else:
                raise ValueError(f"Could not find the matching .rls file for the opened .dtt file ({path}).")

        elif path.suffix.lower() == ".rls":
            # If rls file is tried to be opened, replace extension
            dttfile = path.parent / (path.stem + ".dtt")
            if dttfile.exists():
                self.load_excalibur(dttfile, path)
            else:
                raise ValueError(f"Could not find the matching .dtt file for the opened .rls file ({path}).")

        elif path.suffix.lower() == ".json":
            self.load_json(path)

        else:
            OSError(f'Extension "{path.suffix}" not recognized. Expected ".dtt" or ".json".')

    def load_excalibur(self, dttfile: Union[str, Path], rlsfile: Union[str, Path]) -> None:
        """
        Load Excalibur file format

        Parameters
        ----------
        dttfile : str
            Path to.dtt file
        rlsfile : str
            Path to .rls file
        """
        savemodel = reader.read_excalibur(dttfile, rlsfile)
        self.add_data(savemodel)

    def load_json(self, path: Union[str, Path]) -> None:
        """
        Load json file format

        Parameters
        ----------
        path : str
            Path to .json file
        """
        savemodel = reader.read_json(path)
        self.add_data(savemodel)

    def import_csv(
        self,
        assessments_csv: Union[Path, str, StringIO],
        assessments_sep: str,
        items_csv: Union[Path, str, StringIO],
        items_sep: str,
        assessments_skiprows: int = 0,
        items_skiprows: int = 0,
    ) -> None:

        reader.CSVreader.read(
            self, assessments_csv, assessments_sep, items_csv, items_sep, assessments_skiprows, items_skiprows
        )

    def add_data(self, savemodel: SaveModel) -> None:
        """
        Adds data to project from loaded dictionary

        Parameters
        ----------
        outdict : dictionary
            Dictionary with loaded input data
        """

        # Get data for determining shape
        nexperts = len(savemodel.experts)
        nitems = len(savemodel.items)
        seed = np.array([item.is_seed for item in savemodel.items.values()])
        unique_quantiles = np.unique(
            np.concatenate([item.quantiles for item in savemodel.items.values()])
        ).tolist()
        nquantiles = len(unique_quantiles)
        arr = np.full((nexperts, nquantiles, nitems), np.nan)
        for i, expid in enumerate(savemodel.experts.keys()):
            for j, itemid in enumerate(savemodel.items.keys()):
                estimates = savemodel.assessments[expid][itemid]
                itemqs = savemodel.items[itemid].quantiles
                arr[i, :, j] = [
                    estimates[itemqs.index(q)] if q in itemqs else np.nan for q in unique_quantiles
                ]

        self.project.initialize(
            nexperts=nexperts, nseed=sum(seed), ntarget=nitems - sum(seed), nquantiles=nquantiles
        )

        # Get experts
        self.project.experts.ids[:] = [str(key) for key in savemodel.experts.keys()]
        self.project.experts.names[:] = [exp.name for exp in savemodel.experts.values()]
        self.project.experts.actual_experts[:] = list(range(len(self.project.experts.ids)))

        # Add assessments
        self.project.assessments.array[:, :, :] = arr
        self.project.assessments.estimates.update(
            {
                expertid: {
                    itemid: ExpertAssessment(
                        quantiles=savemodel.items[itemid].quantiles,
                        values=estimates,
                        expertid=expertid,
                        itemid=itemid,
                        scale=savemodel.items[itemid].scale,
                        observer=self.project.assessments.update_array_value,
                        item_lbound=savemodel.items[itemid].bounds[0]
                        if not np.isnan(savemodel.items[itemid].bounds[0])
                        else None,
                        item_ubound=savemodel.items[itemid].bounds[1]
                        if not np.isnan(savemodel.items[itemid].bounds[1])
                        else None,
                    )
                    for itemid, estimates in expertestimates.items()
                }
                for expertid, expertestimates in savemodel.assessments.items()
            }
        )

        # Add quantiles and probabilies per bin
        self.project.assessments.quantiles.clear()
        self.project.assessments.quantiles.extend(sorted(unique_quantiles))
        # self.project.assessments.calculate_binprobs()

        # Add items (questions)
        self.project.items.ids[:] = [str(key) for key in savemodel.items.keys()]
        self.project.items.realizations[:] = [item.realization for item in savemodel.items.values()]
        self.project.items.scales[:] = [item.scale for item in savemodel.items.values()]
        self.project.items.units[:] = [item.unit for item in savemodel.items.values()]
        self.project.items.bounds[:, :] = [item.bounds for item in savemodel.items.values()]
        self.project.items.overshoots[:, :] = [item.overshoots for item in savemodel.items.values()]
        self.project.items.questions[:] = [item.question for item in savemodel.items.values()]
        self.project.items.use_quantiles[:, :] = [
            np.in1d(unique_quantiles, item.quantiles) for item in savemodel.items.values()
        ]

        # # Add results
        # for key, settings in outdict["results"].items():
        #     self.project.add_results_from_settings(settings)
