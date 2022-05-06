"""
Robustness test that first generates calibration and information scores
with robustness routines, and after that uses the regular routine
to check all these numbers
"""


import sys
import unittest
from pathlib import Path

sys.path.append("..")

import anduryl

filedir = Path(__file__).parent
datadir = filedir / "data"
casedir = filedir / ".." / "cases"


class TestRobustness(unittest.TestCase):
    def test1_compare_item_robustness(self):

        alpha = None
        weight = "item"

        # Generate item robustness with robustness routine
        project = anduryl.Project()
        project.io.load_excalibur(casedir / "tobacco.dtt", casedir / "tobacco.rls")

        project.calculate_item_robustness(
            weight_type=weight, overshoot=0.1, max_exclude=2, min_exclude=0, calpower=1.0, alpha=alpha
        )

        # Check each score by opening a new project, removing the items and checking the scores
        print("\nCombinations:", len(project.main_results.item_robustness))
        for key, values in project.main_results.item_robustness.items():

            with self.subTest(key):
                project = anduryl.Project()
                project.io.load_excalibur(casedir / "tobacco.dtt", casedir / "tobacco.rls")

                # Remove items
                for item in key:
                    project.items.remove_item(item)

                # Calculate decision maker
                project.calculate_decision_maker(
                    weight_type=weight,
                    overshoot=0.1,
                    exp_id="exp",
                    exp_name="exp",
                    alpha=alpha,
                    calpower=1.0,
                    overwrite=True,
                )

                # Check if all scores match
                self.assertAlmostEqual(
                    values[2], project.experts.calibration[-1], msg=f'calibration ({", ".join(key)}): '
                )
                self.assertAlmostEqual(values[1], project.experts.info_real[-1], msg=f'info_real ({", ".join(key)}): ')
                self.assertAlmostEqual(
                    values[0], project.experts.info_total[-1], msg=f'info_total ({", ".join(key)}): '
                )

    def test2_compare_expert_robustness(self):

        alpha = None
        weight = "item"

        # Generate item robustness with robustness routine
        project = anduryl.Project()
        project.io.load_excalibur(casedir / "tobacco.dtt", casedir / "tobacco.rls")

        project.calculate_expert_robustness(
            weight_type=weight, overshoot=0.1, max_exclude=3, min_exclude=0, calpower=1.0, alpha=alpha
        )

        # Check each score by opening a new project, removing the items and checking the scores
        print("\nCombinations:", len(project.main_results.expert_robustness))
        for key, values in project.main_results.expert_robustness.items():

            with self.subTest(key):
                project = anduryl.Project()
                project.io.load_excalibur(casedir / "tobacco.dtt", casedir / "tobacco.rls")

                # Remove items
                for expert in key:
                    project.experts.remove_expert(expert)

                # Calculate decision maker
                project.calculate_decision_maker(
                    weight_type=weight,
                    overshoot=0.1,
                    exp_id="exp",
                    exp_name="exp",
                    alpha=alpha,
                    calpower=1.0,
                    overwrite=True,
                )

                # Check if all scores match
                self.assertAlmostEqual(
                    values[2], project.experts.calibration[-1], msg=f'calibration ({", ".join(key)}): '
                )
                self.assertAlmostEqual(values[1], project.experts.info_real[-1], msg=f'info_real ({", ".join(key)}): ')
                self.assertAlmostEqual(
                    values[0], project.experts.info_total[-1], msg=f'info_total ({", ".join(key)}): '
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
