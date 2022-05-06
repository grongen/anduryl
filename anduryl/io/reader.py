import json
import re
from pathlib import Path
from typing import Union

import numpy as np
from anduryl.io.savemodels import SaveModel, Item, Expert


def dict_to_elements(dct: dict) -> list:
    """
    Create a (nested) list from a dictionary

    Parameters
    ----------
    dct : dictionary
        Dictionary to reshape into lists

    Returns
    -------
    list, list
        Labels and elements
    """

    keys = []

    def get_keys(dct, level=0):
        # Verzamel keys
        for key, val in dct.items():
            if len(keys) < level + 1:
                keys.append([])
            keys[level].append(key)
            if isinstance(val, dict):
                get_keys(val, level + 1)

    # Get keys and select unique
    get_keys(dct)
    for i in range(len(keys)):
        keys[i] = list(set(keys[i]))

    def fill_lists_by_key(dct, level=0):
        lst = [None] * len(keys[level])
        for key, val in dct.items():
            idx = keys[level].index(key)
            if isinstance(val, dict):
                lst[idx] = fill_lists_by_key(val, level + 1)
            else:

                lst[idx] = val
        return lst

    items = fill_lists_by_key(dct)

    return keys, items


def read_json(path: Union[str, Path]) -> SaveModel:
    """
    Reads Anduryl project from json format

    Parameters
    ----------
    path : str
        Path to json file

    Returns
    -------
    dictionary
        Dictionary with loaded data
    """

    outdct = {}

    # Write to json
    with open(path, "r") as f:
        dct = json.loads(f.read())

    # Check if a version number is present
    if "version" not in dct:
        savemodel = conv_dct_v1_2_0(dct)
    elif dct["version"] == "1.2.1":
        savemodel = SaveModel.parse_obj(dct)
    else:
        raise ValueError(f"Version {dct['version']} not recognized. Expected 1.2.0 or 1.2.1.")

    return savemodel


def conv_dct_v1_2_0(dct: dict) -> SaveModel:

    # Get savemodel dictionary
    savemodel_dct = {"experts": dct["experts"].copy(), "items": dct["items"].copy(), "assessments": {}}

    # Get expert data
    # for expertid, subdct in dct["experts"].items():
    #     subdct.update(expertid=expertid)
    #     savemodel_dct["experts"].append(subdct)

    # Get item data
    # for itemid, subdct in dct["items"].items():
    #     subdct.update(itemid=itemid)
    #     savemodel_dct["items"].append(subdct)

    # Get used percentiles per item
    itempercentiles = {}
    for expertid, expdct in dct["assessments"].items():
        for itemid, itemdct in expdct.items():
            used_percentiles = set([key for key in sorted(itemdct.keys()) if not np.isnan(itemdct[key])])
            if itemid in itempercentiles:
                itempercentiles[itemid] = used_percentiles.union(itempercentiles[itemid])
            else:
                itempercentiles[itemid] = used_percentiles
    # Add to item dicts
    for itemid, itemdct in savemodel_dct["items"].items():
        itemdct.update(quantiles=sorted(itempercentiles[itemid]))

    # Get savemodel dictionary
    for expertid, expdct in dct["assessments"].items():
        savemodel_dct["assessments"][expertid] = {}
        for itemid, itemdct in expdct.items():
            # Get the percentiles for the question
            # Check if they match the previous percentiles
            savemodel_dct["assessments"][expertid][itemid] = [
                itemdct[p] for p in sorted(itempercentiles[itemid])
            ]

    return SaveModel.parse_obj(savemodel_dct)

    # # Read experts
    # labels, values = dict_to_elements(dct["experts"])
    # exp_dict = dct["experts"]
    # exp_ids = list(exp_dict.keys())
    # outdct["experts"] = {"ids": exp_ids, "name": [exp_dict[exp]["name"] for exp in exp_ids]}

    # # Read items
    # labels, values = dict_to_elements(dct["items"])
    # item_dict = dct["items"]
    # item_ids = list(item_dict.keys())
    # outdct["items"] = {
    #     "ids": item_ids,
    #     "realization": [item_dict[item]["realization"] for item in item_ids],
    #     "scale": [item_dict[item]["scale"] for item in item_ids],
    #     "question": [item_dict[item]["question"] for item in item_ids],
    # }

    # # Read assessments
    # labels, values = dict_to_elements(dct["assessments"])
    # assessments = np.array(values)
    # outdct["quantiles"] = sorted(float(i) for i in labels[-1])

    # # Sort assessments
    # # by experts
    # assessments = np.array(values)[np.argsort([exp_ids.index(exp) for exp in labels[0]]), :, :]
    # # by items
    # assessments = assessments[:, np.argsort([item_ids.index(item) for item in labels[1]])]
    # # by quantiles
    # assessments = assessments[:, :, np.argsort(np.array(labels[2], dtype=float))]
    # # Swap quantiles and items such that the quantiles are in second place
    # outdct["assessments"] = np.swapaxes(assessments, 1, 2)

    # # Add results
    # outdct["results"] = {}  # dct['results']

    # return outdct


def read_excalibur(dttfile: Union[str, Path], rlsfile: Union[str, Path]) -> SaveModel:
    """
    Function to read assessment from Excalibur .ddt and .rls file

    Parameters
    ----------
    dttfile : str
        File with assessments
    rlsfile : str
        File with realisations
    """
    if not isinstance(dttfile, Path):
        dttfile = Path(dttfile)
    if not isinstance(rlsfile, Path):
        rlsfile = Path(rlsfile)

    if not dttfile.exists():
        raise OSError(f"File does not exist: {dttfile}")

    if not rlsfile.exists():
        raise OSError(f"File does not exist: {rlsfile}")

    # Read dtt file
    with dttfile.open("r", errors="replace") as f:
        lines = [line for line in f.readlines() if line.strip()]

    # Get percentiles
    first = lines[0]
    quantiles = np.array([float(p) for p in first.split("QU=")[-1].split()]) / 100
    nquantiles = len(quantiles)

    # Get number of experts and questions
    nexperts = max([int(line.split()[0]) for line in lines[1:]])
    nquestions = max([int(line[14:20]) for line in lines[1:]])

    # Get background measure
    pos = [max(line.lower().find("uni"), line.lower().find("log")) for line in lines]
    u, c = np.unique(pos, return_counts=True)
    startchr = u[np.argmax(c)]
    background = np.array([line[startchr : startchr + 3].lower() for line in lines[1 : 1 + nquestions]])

    # Get question id's
    idstrs = np.array([line[:startchr] for line in lines[1 : 1 + nquestions]])
    ids = []
    for line in idstrs:
        #  {:4d} {:>8s} {:4d} {:>14s}
        # 1 + 4 + 1 + 8 + 1 + 4 + 1 = 20
        # Find a pattern of [group of decimals, space, something, space, group of decimals]
        ids.append(line[20:].strip())
        # pattern = re.findall("([^\s]+\s+[^\s]+\s+[^\s]+)", line.strip())[0]
        # ids.append(line[line.find(pattern) + len(pattern) :].strip())

    # Get expert ids
    experts = np.array([lines[i][5:14].strip() for i in range(1, len(lines), nquestions)])

    # Assessments
    # assessments = np.zeros((nexperts, nquantiles, nquestions))
    # for line in lines[1:]:
    #     iexpert = int(line[:5])
    #     iquestion = int(line[14:20])
    #     assessments[iexpert - 1, :, iquestion - 1] = line[startchr + 3 :].split()[:nquantiles]
    # # Process 'no-data'
    # assessments = assessments.astype(float)
    # assessments[(assessments >= -1000) & (assessments <= -990)] = np.nan

    assessments = {}
    for line in lines[1:]:
        iexpert = experts[int(line[:5]) - 1]
        iitem = ids[int(line[15:20]) - 1]

        if iexpert not in assessments:
            assessments[iexpert] = {}

        estimates = np.array(line[startchr + 3 :].split()[:nquantiles], dtype=float)
        estimates[(estimates >= -1000) & (estimates <= -990)] = np.nan
        assessments[iexpert][iitem] = estimates.tolist()

    # Read realisations from rls file
    with rlsfile.open("r", errors="replace") as f:
        lines = [line for line in f.readlines() if line.strip()]

    # Get the position of 'uni' of 'log' in the file
    pos = [max(line.lower().find("uni"), line.lower().find("log")) for line in lines]
    u, c = np.unique(pos, return_counts=True)
    endchr = u[np.argmax(c)]

    realdict = {}
    questiondict = {}
    for line in lines:
        value = line[:endchr].split()[-1]
        linepart = line[: line.find(value)].strip()
        qid = re.findall("[^\s]+(.+)", linepart)[0].strip()
        realdict[qid] = value
        questiondict[qid] = line[endchr + 3 :].strip()

    realizations = np.array([float(realdict[key]) if key in realdict else -995 for key in ids])
    questions = [questiondict[key] if key in questiondict else "" for key in ids]

    # Process 'no-data'
    idx = (realizations >= -1000) & (realizations <= -990)
    realizations = np.array([np.nan if idx[i] else val for i, val in enumerate(realizations)], dtype=object)

    outdict = {
        "assessments": assessments,
        "items": {
            itemid: dict(realization=r, scale=s, question=q, quantiles=quantiles.tolist())
            for (itemid, r, s, q) in zip(ids, realizations, np.array(background).astype(object).T, questions)
        },
        "experts": {expertid: dict(name=expertid) for expertid in experts},
    }

    savemodel = SaveModel.parse_obj(outdict)

    return savemodel


class CSVreader:
    def __init__(
        self,
        assessments_csv: Union[Path, str],
        assessments_sep: str,
        items_csv: Union[Path, str],
        items_sep: str,
        assessments_skiprows: int = 0,
        items_skiprows: int = 0,
    ) -> None:

        self.assessments_csv = assessments_csv
        self.assessments_sep = assessments_sep
        self.items_csv = items_csv
        self.items_sep = items_sep
        self.assessments_skiprows = assessments_skiprows
        self.items_skiprows = items_skiprows

        self._check_paths()

        self.item_cols = ["itemid", "realization", "scale", "question"]
        self.item_cols_mandatory = ["itemid", "realization", "scale"]
        self._items = {}

        self._experts = {}

        self.assessment_cols_mandatory = ['itemid', 'expertid']
        self._assessments = {}

    @classmethod
    def read(cls,
        project,
        assessments_csv: Union[Path, str],
        assessments_sep: str,
        items_csv: Union[Path, str],
        items_sep: str,
        assessments_skiprows: int = 0,
        items_skiprows: int = 0):
        
        csvreader = cls(assessments_csv, assessments_sep, items_csv, items_sep, assessments_skiprows, items_skiprows)
        csvreader.read_items()
        csvreader.read_assessments()
        savemodel = csvreader.to_savemodel()
        project.add_data(savemodel)

    def _check_paths(self) -> None:
        # Convert to Path, if not already
        if not isinstance(self.assessments_csv, Path):
            self.assessments_csv = Path(self.assessments_csv)
        if not isinstance(self.items_csv, Path):
            self.items_csv = Path(self.items_csv)

        files = [self.assessments_csv, self.items_csv]

        # Check if path exists:
        for file in files:
            if not file.exists():
                raise OSError(f'Path "{file.resolve()}" does not exist.')


    def read_items(self) -> None:

        # Read items
        with self.items_csv.open("r") as f:
            itemlines = [line.strip() for line in f.readlines()[self.items_skiprows :]]

        # Read header
        header = [key.lower() for key in itemlines.pop(0).split(self.items_sep)]

        # Check if all mandatory columns are present
        for key in self.item_cols_mandatory:
            if key not in header:
                raise KeyError(f'Did not find column "{key}" in csv with items.')

        # Get the position of each column in csv
        colpos = {key: header.index(key) for key in self.item_cols if key in header}
        ikey = colpos.pop("itemid")

        # Add to dict of items. Use pydantic class to validate item
        self._items.clear()
        for line in itemlines:
            parts = line.split(self.items_sep)
            itemdct = {'quantiles': []}
            for key, i in colpos.items():
                if key == 'realization' and parts[i] == '':
                    itemdct[key] = np.nan
                else:
                    itemdct[key] = parts[i]
            self._items.update(
                {parts[ikey]: Item.parse_obj(itemdct)}
            )

    def read_assessments(self) -> None:

        # Check if items are read
        if len(self._items) == 0:
            raise ValueError('The items have not been read')

        # Read lines
        with self.assessments_csv.open("r") as f:
            assessmentlines = [line.strip() for line in f.readlines()[self.assessments_skiprows :]]

        # Get the quantiles from the header
        header = [key.lower() for key in assessmentlines.pop(0).split(self.assessments_sep)]

        # Check if all mandatory columns are present
        for key in self.assessment_cols_mandatory:
            if key not in header:
                raise KeyError(f'Did not find column "{key}" in csv with assessments.')

        # Get position of expert and item in header    
        colpos = {key: header.index(key) for key in self.assessment_cols_mandatory}

        # The remaining columns are quantiles
        for key in self.assessment_cols_mandatory:
            header.remove(key)
        quantiles = [float(item) for item in header]
        for i, q in enumerate(quantiles):
            if not 0.0 <= q <= 1.0:
                raise ValueError(f'Expected a quantile value in between 0 and 1, got "{q}"')
            if i > 0:
                if not quantiles[i] > quantiles[i - 1]:
                    raise ValueError("Quantiles should be monotonuous increasing.")

        # Add quantiles to items.
        for key, item in self._items.items():
            self._items[key].quantiles = quantiles

        # Read the experts, check the items
        self._experts.clear()
        for line in assessmentlines:
            parts = line.split(self.assessments_sep)
            # Add expert if not present
            expert = parts[colpos['expertid']]
            if expert not in self._experts:
                self._experts.update({expert: Expert()})
                self._assessments[expert] = {}
            
            # Check if item is present
            item = parts[colpos['itemid']]
            if item not in self._items:
                raise ValueError(f'Item "{item}" in assessments not found in list of given items.')

            for i in reversed(sorted(colpos.values())):
                parts.remove(parts[i])
            
            estimates = parts
            if len(estimates) != len(quantiles):
                raise ValueError(f'Got "{len(estimates)}" estimates for "{len(quantiles)}" quantiles.')

            self._assessments[expert][item] = estimates

    def to_savemodel(self) -> SaveModel:

        # Add to dictionary, and return parsed dictionary
        outdict = {
            "assessments": self._assessments,
            "items": self._items,
            "experts": self._experts,
        }
        return SaveModel.parse_obj(outdict)


    # def add_to_project(self, project):

    #     self.project.initialize(nexperts=len(experts), nseed=0, ntarget=len(items), nquantiles=len(quantiles))

    #     # Get experts
    #     self.project.experts.ids[:] = experts
    #     self.project.experts.names[:] = [""] * len(experts)
    #     self.project.experts.actual_experts[:] = list(range(len(self.project.experts.ids)))

    #     # Add quantiles and probabilies per bin
    #     del self.project.assessments.quantiles[:]
    #     self.project.assessments.quantiles.extend(quantiles)

    #     # Add items (questions)
    #     self.project.items.ids[:] = items
    #     self.project.items.realizations[:] = np.nan
    #     self.project.items.scales[:] = ["uni"] * len(items)

        