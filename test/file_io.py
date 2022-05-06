"""Test to check if input file are re-read to the same data structure as json ans excalibur format"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append("..")

import anduryl
from anduryl.io import reader, table
from anduryl.ui.models import AssessmentArrayModel
from anduryl.ui.main import Signals

filedir = Path(__file__).parent
datadir = filedir / "data"
casedir = filedir / ".." / "cases"


excalibur_files = {
    "Arkansas": "Arkansas",
    "Arsenic": "arsenic d-r",
    "ATCEP": "ATCEP Error",
    "Biol_Agent": "Biol agents",
    "CDC_ROI": "CDC ROI Final",
    "CoveringKids": "CoveringKids",
    "create-vicki": "create",
    "CWD": "cwd",
    "Daniela": "Daniela",
    "DCPN_Fistula": "dcpn_fistula",
    "eBPP": "ebbp",
    "Eff_Erup": "EffusiveErupt",
    "Erie_Carp": "Erie Carps",
    "FCEP": "FCEP Error",
    "Florida": "Florida",
    "Gerstenberger": "Gerstenberger",
    "GL_NIS": "gl-nis",
    "Goodheart": "Goodheart",
    "Hemopilia": "Hemophilia",
    "IceSheets": "IceSheet2012",
    "Illinois": "Illinois",
    "Liander": "liander",
    "Nebraska": "Nebraska",
    "Obesity": "obesity_ms",
    "PHAC_T4": "PHAC 2009 final",
    "San_Diego": "San Diego",
    "Sheep": "Sheep Scab",
    "SPEED": "speed",
    "TDC": "tdc",
    "Tobacco": "tobacco",
    "Topaz": "Topaz",
    "UMD_NREMOVAL": "umd_nremoval",
    "Washington": "Washington",
}


class TestDataDirExists(unittest.TestCase):
    if not datadir.exists():
        raise OSError(f'Directory "{Path(".").resolve() /  datadir}" does not exist')
    if not casedir.exists():
        raise OSError(f'Directory "{Path(".").resolve() /  casedir}" does not exist')


class TestFromExcalibur(unittest.TestCase):
    def test1_from_excalibur(self):
        def compare_dict_recursive(dict1, dict2, casename=""):
            for (key, value1) in dict1.items():
                if key not in dict2:
                    raise KeyError(f"Key {key} not present in dictionary 2")

                value2 = dict2[key]
                msg = f"Differences found for case: {casename}, {key}"

                if isinstance(value1, dict):
                    compare_dict_recursive(value1, value2, casename)

                elif isinstance(value1, (int, float)):
                    np.testing.assert_equal(value1, value2)

                elif isinstance(value1, list):
                    np.testing.assert_equal(value1, value2)

                elif isinstance(value1, tuple):
                    np.testing.assert_equal(value1, value2)

        # Loop over all datasets
        for casename, file in excalibur_files.items():

            # Create project and load excalibur data file
            project = anduryl.Project()
            savemodel1 = reader.read_excalibur(casedir / f"{file}.dtt", casedir / f"{file}.rls")
            project.io.add_data(savemodel1)

            # Save to excalibur
            project.io.to_excalibur(dttfile="tmp.dtt")

            # Load again from excalibur
            project = anduryl.Project()
            savemodel2 = reader.read_excalibur("tmp.dtt", "tmp.rls")
            project.io.add_data(savemodel2)

            # Check for differences
            for (key, subdict1) in savemodel1.dict().items():
                # Ther version does not need to be equal
                if key == "version":
                    continue

                subdict2 = savemodel2.dict()[key]
                compare_dict_recursive(subdict1, subdict2, casename + " - excalibur")

            # Save to json
            project.io.to_json("tmp.json")

            # Load again from excalibur
            project = anduryl.Project()
            savemodel3 = reader.read_json("tmp.json")

            # Check for differences
            for (key, subdict2) in savemodel2.dict().items():
                # Ther version does not need to be equal
                if key == "version":
                    continue

                subdict3 = savemodel3.dict()[key]
                compare_dict_recursive(subdict2, subdict3, casename + " - json")

        Path("tmp.dtt").unlink()
        Path("tmp.rls").unlink()
        Path("tmp.json").unlink()


class TestImportCSV(unittest.TestCase):
    def test2_import_csv(self):

        # Create project and load excalibur data file
        project = anduryl.Project()

        assessments_csv = Path("test/data/tobacco_csv_assessments.csv")
        assessments_sep = ";"
        assessments_skiprows = 0

        items_csv = Path("test/data/tobacco_csv_items.csv")
        items_sep = ";"
        items_skiprows = 0

        # Read csv
        project.io.import_csv(
            assessments_csv=assessments_csv,
            assessments_sep=assessments_sep,
            items_csv=items_csv,
            items_sep=items_sep,
            assessments_skiprows=assessments_skiprows,
            items_skiprows=items_skiprows,
        )

        # Check if the read tables are parsed tables the same
        model = AssessmentArrayModel(project)
        parsed_lines = table.get_table_text(model, newline="\n", delimiter=assessments_sep).strip().split("\n")

        read_lines = assessments_csv.open("r").read().strip().split("\n")
        for i in range(1, len(parsed_lines)):
            self.assertEqual(read_lines[i], parsed_lines[i])


if __name__ == "__main__":

    unittest.main(verbosity=2)
