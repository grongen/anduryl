import json
from pathlib import Path

import numpy as np
from anduryl.io.table import get_table_text
from PyQt5 import QtWidgets


def table_to_csv(model, mainwindow, path: Path = None):
    """
    Saves table to csv.

    Parameters
    ----------
    model : table model
        Table model from which the data is retrieved
    mainwindow : mainwindow
        Is used for retrieving save file name
    path : str, optional
        Path to save file, if None, the user is asked to provide the save file name
    """

    if path is None:
        options = QtWidgets.QFileDialog.Options() | QtWidgets.QFileDialog.DontUseNativeDialog
        # Set current dir
        currentdir = mainwindow.appsettings.value("currentdir", ".", type=str)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            mainwindow, "Anduryl - Save as CSV", ".", "CSV (*.csv)", options=options
        )

    if not path:
        return None

    if not path.parent.exists():
        raise OSError(f'Save path "{path.parent}" does not exists.')

    if not path.endswith(".csv"):
        path += ".csv"

    with open(path, "w") as f:
        f.write(get_table_text(model, newline="\n", delimiter=";"))


def write_json(project, path: Path):
    """
    Function to write project experts, items and assessments
    to .json

    Results are not writen to the file. Expert names are also
    not saved.

    Parameters
    ----------
    project : Project instance
        Project with experts, items and assessments
    path : str
        Path to .json file
    """

    # Check if paths exists
    if not isinstance(path, Path):
        path = Path(path)

    if not path.parent.exists():
        raise OSError(f'Directory "{path.parent}" does not exists.')

    expert_data_T = list(zip(*[project.experts.names, project.experts.user_weights]))
    expert_data_T = [expert_data_T[i] for i in project.experts.actual_experts]

    # Create dictionary
    savedct = {
        "experts": elements_to_dict(
            expert_data_T, [project.experts.get_exp("actual"), ["name", "user weight"]]
        ),
        "items": elements_to_dict(
            list(zip(*[project.items.realizations, project.items.scales, project.items.questions])),
            [project.items.ids, ["realization", "scale", "question"]],
        ),
        "assessments": elements_to_dict(
            np.swapaxes(project.assessments.array, 1, 2)[project.experts.actual_experts],
            [project.experts.get_exp("actual"), project.items.ids, project.assessments.quantiles],
        ),
        # "results": {key: project.results[key].settings for key in project.results.keys()},
    }

    # Write to json
    with open(path, "w") as f:
        f.write(savedct.model_dump_json(indent=4))


def write_excalibur(project, dttfile, rlsfile):
    """
    Function to write project experts, items and assessments
    to .dtt and .rls files.

    Results are not writen to the file. Expert names are also
    not saved.

    Parameters
    ----------
    project : Project instance
        Project with experts, items and assessments
    dttfile : str
        Path to .dtt file
    rlsfile : str
        Path to .rls file
    """

    # Check if paths exists
    for path in [dttfile, rlsfile]:
        if not isinstance(path, Path):
            path = Path(path)
        if not path.parent.exists():
            raise OSError(f'Directory "{path.parent}" does not exists.')

    quantiles = project.assessments.quantiles
    _, nquantiles, nitems = project.assessments.array.shape
    nexperts = len(project.experts.actual_experts)

    # Get ID's with max string length
    expertids = [
        expid[: min(len(expid), 8)]
        for i, expid in enumerate(project.experts.ids)
        if i in project.experts.actual_experts
    ]
    itemids = [itemid[: min(len(itemid), 14)] for itemid in project.items.ids]

    assessments = project.assessments.array[project.experts.actual_experts, :, :]
    assessments[np.isnan(assessments)] = -999.5

    # dtt
    quantiles_str = "  ".join([f"{int(round(100*quantile)):2d}" for quantile in quantiles])
    dtttext = f"* CLASS ASCII OUTPUT FILE. NQ= {len(quantiles):3d}   QU=  " + quantiles_str + "\n"

    # Construct format for line without and with question
    line = " {:4d} {:>8s} {:4d} {:>14s} {:>3s} " + " ".join(["{}"] * len(quantiles)) + " \n"
    questionline = " {:4d} {:>8s} {:4d} {:>14s} {:>3s} " + " ".join(["{}"] * len(quantiles)) + " {:>173s} \n"

    for iexp, expert in enumerate(expertids):
        for iit, (item, scale, question) in enumerate(
            zip(itemids, project.items.scales, project.items.questions)
        ):
            # Collect values in correct scientific format
            values = [
                ("" if val < 0 else " ")
                + np.format_float_scientific(val, unique=False, exp_digits=4, precision=5)
                for val in assessments[iexp, :, iit]
            ]
            # Write question if they are specified and first expert or first item
            if question and (iexp == 0 or iit == 0):
                dtttext += questionline.format(iexp + 1, expert, iit + 1, item, scale, *values, question)
            # Else write a line without questions
            else:
                dtttext += line.format(iexp + 1, expert, iit + 1, item, scale, *values)

    # rls
    questionline = " {:4d} {:>14s} {} {:>3s} {:>173s} \n"
    rlstext = ""
    realizations = project.items.realizations.copy()
    realizations[np.isnan(realizations)] = -999.5

    for iit, (item, scale, question, val) in enumerate(
        zip(itemids, project.items.scales, project.items.questions, realizations)
    ):
        value = ("" if val < 0 else " ") + np.format_float_scientific(
            val, unique=False, exp_digits=4, precision=5
        )
        rlstext += questionline.format(iit + 1, item, value, scale, question)

    with open(dttfile, "w") as f:
        f.write(dtttext)

    with open(rlsfile, "w") as f:
        f.write(rlstext)


def elements_to_dict(arr, labels, level=0):
    """
    Functionn to map array of list elements to dictionary

    Parameters
    ----------
    arr : np.ndarray or lists
        Elements to be ravelled to dict
    labels : list
        labels for each 'axis' of the arr
    level : int, optional
        Level of depth, used by the function itself when nesting, by default 0

    Returns
    -------
    dictionary
        array as ravelled dictionary
    """
    dct = {}
    for i, item in enumerate(arr):
        key = labels[level][i]
        if isinstance(item, (np.ndarray, list, tuple)):
            dct[key] = elements_to_dict(item, labels, level + 1)
        else:
            dct[key] = item

    return dct
