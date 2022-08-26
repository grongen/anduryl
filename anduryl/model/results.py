from anduryl.model.assessment import ExpertAssessment, EmpiricalAssessment
from anduryl.io.settings import Distribution

import numpy as np


class PlotData:
    def __init__(self, assessment, quantiles, distribution, lower, upper, full_dm_cdf=True):

        self.lower = lower
        self.upper = upper
        self.distribution = distribution

        # Get plotdata
        if isinstance(assessment, ExpertAssessment):
            if distribution == Distribution.PWL:
                self._get_pwl_cdf(assessment)
            elif distribution == Distribution.METALOG:
                self._get_metalog_cdf(assessment)
            else:
                raise TypeError(distribution)
            # Get the estimates
            self.estimates = assessment.estimates.copy()

        elif isinstance(assessment, EmpiricalAssessment):
            self._get_empirical_cdf(assessment, full_dm_cdf)
            # Get the interpolated estimates
            self.estimates = dict(
                zip(quantiles, np.interp(quantiles, *list(zip(*assessment.estimates.items()))))
            )

    def _get_pwl_cdf(self, assessment):
        value = np.array(list(assessment.estimates.values()))
        cd = np.array(list(assessment.estimates.keys()))

        # Convert such that data is easily accessible for plots
        self.cdf_x = np.concatenate([[self.lower], value, [self.upper]])
        self.cdf_y = np.concatenate([[0.0], cd, [1.0]])

        self._get_pdf_stepped()

        return value, cd

    def _get_metalog_cdf(self, assessment):
        value = assessment.metalog.pps[:]
        cd = assessment.metalog.prange[:]

        # Convert such that data is easily accessible for plots
        self.cdf_x, index = np.unique(value, return_index=True)
        self.cdf_y = cd[index]
        self._get_pdf_derivative()

        return value, cd

    def _get_empirical_cdf(self, assessment, full_dm_cdf):
        if not full_dm_cdf:
            return self._get_pwl_cdf(assessment)
        value = assessment.xp[:]
        cd = assessment.fp[:]

        # Convert such that data is easily accessible for plots
        self.cdf_x, index = np.unique(value, return_index=True)
        self.cdf_y = cd[index]

        if self.distribution == Distribution.PWL:
            self._get_pdf_stepped()
        elif self.distribution == Distribution.METALOG:
            self._get_pdf_derivative()

        return value, cd

    def _get_pdf_stepped(self):
        # Calculate the denisty for the pdf values
        self.pdf_x = np.repeat(self.cdf_x, 2)
        binprobs = self.cdf_y[1:] - self.cdf_y[:-1]
        # if ((self.cdf_x[1:] - self.cdf_x[:-1]) <= 0.0).any():
            # raise ValueError()
        pdensity = binprobs / (self.cdf_x[1:] - self.cdf_x[:-1])
        self.pdf_y = np.r_[0, np.repeat(pdensity, 2), 0.0]

    def _get_pdf_derivative(self):
        # Calculate the denisty for the pdf values
        diff_x = self.cdf_x[1:] - self.cdf_x[:-1]
        diff_y = self.cdf_y[1:] - self.cdf_y[:-1]
        self.pdf_x = (self.cdf_x[1:] + self.cdf_x[:-1]) * 0.5
        self.pdf_y = diff_y / diff_x
