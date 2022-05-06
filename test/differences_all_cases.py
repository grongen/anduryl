import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.append("..")

import anduryl

performance_test = True

if not performance_test:
    import pandas as pd


filedir = Path(__file__).parent
datadir = filedir / "data"
casedir = filedir / ".." / "cases"


datasets = {
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


class TestCompareAllCases(unittest.TestCase):
    def setUp(self):
        if not performance_test:
            self.validation_table = pd.read_csv(
                (datadir / "Anduryl.csv").resolve(), sep=";", header=[0, 1], index_col=0
            )

    def test1_compare_all_cases(self):

        if not performance_test:
            anduryl_table = self.validation_table.copy()
            anduryl_table.iloc[:, 2:] = np.nan

        # Show full message if not equal
        self.maxDiff = None

        # Loop over all datasets
        for casename, file in datasets.items():

            # Create project and load excalibur data file
            project = anduryl.Project()
            project.io.load_excalibur(
                (casedir / f"{file}.dtt").resolve(), (casedir / f"{file}.rls").resolve()
            )

            # Item weights optimized
            project.calculate_decision_maker(
                weight_type="item", overshoot=0.1, exp_id="DM1", exp_name="Item opt."
            )
            itemopt = np.round(
                [
                    project.experts.calibration[-1],
                    project.experts.info_real[-1],
                    project.experts.info_real[-1] * project.experts.calibration[-1],
                ],
                2,
            )

            # Global weights optimized
            project.calculate_decision_maker(
                weight_type="global",
                overshoot=0.1,
                exp_id="DM2",
                exp_name="Global opt.",
            )
            globopt = np.round(
                [
                    project.experts.calibration[-1],
                    project.experts.info_real[-1],
                    project.experts.info_real[-1] * project.experts.calibration[-1],
                ],
                2,
            )

            # Global weights non-optimized
            project.calculate_decision_maker(
                weight_type="global",
                alpha=0.0,
                overshoot=0.1,
                exp_id="DM3",
                exp_name="Global Non-opt.",
            )
            globnonopt = np.round(
                [
                    project.experts.calibration[-1],
                    project.experts.info_real[-1],
                    project.experts.info_real[-1] * project.experts.calibration[-1],
                ],
                2,
            )

            # Equal weights
            project.calculate_decision_maker(
                weight_type="equal", overshoot=0.1, exp_id="DM4", exp_name="Equal"
            )
            equal = np.round(
                [
                    project.experts.calibration[-1],
                    project.experts.info_real[-1],
                    project.experts.info_real[-1] * project.experts.calibration[-1],
                ],
                2,
            )

            # Get best expert
            imax = np.argmax([project.experts.comb_score[i] for i in project.experts.actual_experts])
            ibest = project.experts.actual_experts[imax]
            best_exp = np.round(
                [
                    project.experts.calibration[ibest],
                    project.experts.info_real[ibest],
                    project.experts.info_real[ibest] * project.experts.calibration[ibest],
                ],
                2,
            )

            if not performance_test:
                # Add results to table
                for i, name in enumerate(["Sa", "Inf", "Comb"]):
                    anduryl_table.at[casename, ("PW Global", name)] = globopt[i]
                    anduryl_table.at[casename, ("PW Non-optimized", name)] = globnonopt[i]
                    anduryl_table.at[casename, ("PW Item", name)] = itemopt[i]
                    anduryl_table.at[casename, ("Equal weight", name)] = equal[i]
                    anduryl_table.at[casename, ("Best Expert", name)] = best_exp[i]

                # Compare
                self.assertDictEqual(
                    self.validation_table.loc[casename].to_dict(),
                    anduryl_table.loc[casename].to_dict(),
                    msg=f"Differences found for case: {casename}",
                )


if __name__ == "__main__":

    unittest.main(verbosity=2)
