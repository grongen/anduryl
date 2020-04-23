import sys
import unittest

import numpy as np
import pandas as pd

sys.path.append('../..')

import anduryl

datasets = {
    'Arkansas': 'Arkansas',
    'Arsenic': 'arsenic d-r',
    'ATCEP': 'ATCEP Error',
    'Biol_Agent': 'Biol agents',
    'CDC_ROI': 'CDC ROI Final',
    'CoveringKids': 'CoveringKids',
    'create-vicki': 'create',
    'CWD': 'cwd',
    'Daniela': 'Daniela',
    'DCPN_Fistula': 'dcpn_fistula',
    'eBPP': 'ebbp',
    'Eff_Erup': 'EffusiveErupt',
    'Erie_Carp': 'Erie Carps',
    'FCEP': 'FCEP Error',
    'Florida': 'Florida',
    'Gerstenberger': 'Gerstenberger',
    'GL_NIS': 'gl-nis',
    'Goodheart': 'Goodheart',
    'Hemopilia': 'Hemophilia',
    'IceSheets': 'IceSheet2012',
    'Illinois': 'Illinois',
    'Liander': 'liander',
    'Nebraska': 'Nebraska',
    'Obesity': 'obesity_ms',
    'PHAC_T4': 'PHAC 2009 final',
    'San_Diego': 'San Diego',
    'Sheep': 'Sheep Scab',
    'SPEED': 'speed',
    'TDC': 'tdc',
    'Tobacco': 'tobacco',
    'Topaz': 'Topaz',
    'UMD_NREMOVAL': 'umd_nremoval',
    'Washington': 'Washington'
}

class TestCompareAllCases(unittest.TestCase):

    def setUp(self):
        self.validation_table = pd.read_csv('data/Anduryl.csv', sep=';', header=[0, 1], index_col=0)

    def test1_compare_all_cases(self):
        
        anduryl_table = self.validation_table.copy()
        anduryl_table.iloc[:, 2:] = np.nan

        # Show full message if not equal
        self.maxDiff = None
        
        # Loop over all datasets
        for key, file in datasets.items():

            # Create project and load excalibur data file
            project = anduryl.Project()
            project.io.load_excalibur(f'../data/{file}.dtt', f'../data/{file}.rls')

            # Item weights optimized
            project.calculate_decision_maker(weight_type='item', overshoot=0.1, exp_id='DM1', exp_name='Item opt.')
            itemopt = np.round([project.experts.calibration[-1], project.experts.info_real[-1], project.experts.info_real[-1] * project.experts.calibration[-1]], 2)

            # Global weights optimized
            project.calculate_decision_maker(weight_type='global', overshoot=0.1, exp_id='DM2', exp_name='Global opt.')
            globopt = np.round([project.experts.calibration[-1], project.experts.info_real[-1], project.experts.info_real[-1] * project.experts.calibration[-1]], 2)

            # Global weights non-optimized
            project.calculate_decision_maker(weight_type='global', alpha=0.0, overshoot=0.1, exp_id='DM3', exp_name='Global Non-opt.')
            globnonopt = np.round([project.experts.calibration[-1], project.experts.info_real[-1], project.experts.info_real[-1] * project.experts.calibration[-1]], 2)

            # Equal weights
            project.calculate_decision_maker(weight_type='equal', overshoot=0.1, exp_id='DM4', exp_name='Equal')
            equal = np.round([project.experts.calibration[-1], project.experts.info_real[-1], project.experts.info_real[-1] * project.experts.calibration[-1]], 2)

            # Get best expert
            imax = np.argmax([project.experts.weights[i] for i in project.experts.actual_experts])
            ibest = project.experts.actual_experts[imax]
            best_exp = np.round([project.experts.calibration[ibest], project.experts.info_real[ibest], project.experts.info_real[ibest] * project.experts.calibration[ibest]], 2)
            
            # Add results to table
            anduryl_table.loc[key, 'PW Global'] = globopt
            anduryl_table.loc[key, 'PW Non-optimized'] = globnonopt
            anduryl_table.loc[key, 'PW Item'] = itemopt
            anduryl_table.loc[key, 'Equal weight'] = equal
            anduryl_table.loc[key, 'Best Expert'] = best_exp

            # Compare
            self.assertDictEqual(self.validation_table.loc[key].to_dict(), anduryl_table.loc[key].to_dict(), msg=f'\nDifferences found for case: {key}')

if __name__ == "__main__":
    unittest.main(verbosity=2)
