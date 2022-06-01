import sys
import unittest

import numpy as np
import pandas as pd

sys.path.append("../..")

import anduryl
from anduryl.io.settings import WeightType

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


class TestCompareAllCases(unittest.TestCase):
    def setUp(self):
        self.validation_table = pd.read_csv("data/Anduryl.csv", sep=";", header=[0, 1], index_col=0)

    def test1_compare_all_cases(self):

        anduryl_table = self.validation_table.copy()
        anduryl_table.iloc[:, 2:] = np.nan

        numsign = []
        info = []
        cali = []

        # Show full message if not equal
        self.maxDiff = None

        # Loop over all datasets
        for casename, file in datasets.items():

            with self.subTest(casename):

                # Create project and load excalibur data file
                project = anduryl.Project()
                project.io.load_excalibur(f"../data/{file}.dtt", f"../data/{file}.rls")

                # Global weights non-optimized
                project.calculate_decision_maker(
                    weight_type=WeightType.GLOBAL,
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
                idx = project.experts.actual_experts
                numsign.append(sum(project.experts.calibration[idx] > 0.05) / len(idx))
                idx = project.experts.actual_experts
                info.append(project.experts.info_total[idx].tolist())
                cali.append(project.experts.calibration[idx].tolist())

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
                    weight_type=WeightType.GLOBAL, overshoot=0.1, exp_id="DM2", exp_name="Global opt."
                )
                globopt = np.round(
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

                result = {
                    ("PW Global", "Sa"): globopt[0],
                    ("PW Global", "Inf"): globopt[1],
                    ("PW Global", "Comb"): globopt[2],
                    ("PW Non-optimized", "Sa"): globnonopt[0],
                    ("PW Non-optimized", "Inf"): globnonopt[1],
                    ("PW Non-optimized", "Comb"): globnonopt[2],
                    ("PW Item", "Sa"): itemopt[0],
                    ("PW Item", "Inf"): itemopt[1],
                    ("PW Item", "Comb"): itemopt[2],
                    ("Equal weight", "Sa"): equal[0],
                    ("Equal weight", "Inf"): equal[1],
                    ("Equal weight", "Comb"): equal[2],
                    ("Best Expert", "Sa"): best_exp[0],
                    ("Best Expert", "Inf"): best_exp[1],
                    ("Best Expert", "Comb"): best_exp[2],
                }

                checkdct = self.validation_table.loc[casename].to_dict()
                del checkdct[("Characteristics", "#Cal")]
                del checkdct[("Characteristics", "#Exp")]

                # Compare
                self.assertDictEqual(checkdct, result, msg=f"Differences found for case: {casename}")

        print(np.mean(numsign), np.percentile(numsign, [5, 50, 75, 95]))

        import matplotlib.pyplot as plt
        from scipy.stats import spearmanr

        ranks = [spearmanr(i, c).correlation for i, c in zip(info, cali)]
        print((np.array(ranks) < 0).sum(), len(ranks), print(np.median(ranks)))
        coefs = [np.corrcoef(i, c)[0, 1] for i, c in zip(info, cali)]
        fig, ax = plt.subplots()
        ax.hist(ranks, range=(-1, 1), bins=10, alpha=0.5)
        ax.hist(coefs, range=(-1, 1), bins=10, alpha=0.5)

        fig, ax = plt.subplots()
        for i, c in zip(info, cali):
            ax.scatter(i, c)
        ax.set_yscale("log")
        plt.show()


if __name__ == "__main__":
    unittest.main(verbosity=3)
