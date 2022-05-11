import sys
from pathlib import Path

import numpy as np
from scipy.stats import cramervonmises

githubpath = Path("d:/Documents/GitHub/metalogistic")
if str(githubpath) not in sys.path:
    sys.path.append(str(githubpath))

import metalogistic


class CustomMetaLogistic(metalogistic.main._MetaLogisticMonoFit):
    def __init__(
        self,
        cdf_ps=None,
        cdf_xs=None,
        term=None,
        fit_method=None,
        lbound=None,
        ubound=None,
        feasibility_method="SmallMReciprocal",
    ):

        super().__init__(super_class_call_only=True)

        if term is not None:
            allow_fallback = False

        self.cdf_ps = cdf_ps
        self.cdf_xs = cdf_xs
        self.cdf_len = len(cdf_ps)

        self.lbound = lbound
        self.ubound = ubound

        user_kwargs = {
            "cdf_ps": cdf_ps,
            "cdf_xs": cdf_xs,
            "term": term,
            "lbound": lbound,
            "ubound": ubound,
            "feasibility_method": feasibility_method,
        }

        self.fit_method_requested = fit_method
        self.term_requested = term

        #  Try linear least squares
        self.candidate = metalogistic.main._MetaLogisticMonoFit(
            **user_kwargs, fit_method="Linear least squares"
        )

    def candidate_is_feasible(self) -> bool:
        """Determines if a candidate is feasible, by calculating a series of percentile
        points, and determining if the resulting cdf values are monotone.

        Returns:
            bool: Whether the candidate is feasible
        """
        eps = 0.001
        y = np.linspace(eps, 1 - eps, 50)
        x = self.candidate.ppf(q=y)
        return (x[1:] > x[:-1]).all()


def get_valid_metalog(ps, xs):
    # Check if the unbounded candidate is feasible
    unbounded = CustomMetaLogistic(cdf_xs=xs, cdf_ps=ps)
    if unbounded.candidate_is_feasible():
        dist = unbounded.candidate

    else:

        # Check if the skewness is towards the lower or upper end
        lower_interquantile = xs[1] - xs[0]
        upper_interquantile = xs[2] - xs[1]
        steps = np.logspace(start=np.log10(1e-2), stop=np.log10(1e2), num=30)

        if lower_interquantile < upper_interquantile:
            steps = xs[0] - (steps * lower_interquantile)
            for lbound in steps[::-1]:
                lowerbounded = CustomMetaLogistic(cdf_xs=xs, cdf_ps=ps, lbound=lbound)
                if lowerbounded.candidate_is_feasible():
                    dist = lowerbounded.candidate
                    break
            else:
                raise ValueError(f"Did not find a suitable lower bound for values {xs}.")

        else:
            steps = xs[-1] + (steps * upper_interquantile)
            for ubound in steps[::-1]:
                upperbounded = CustomMetaLogistic(cdf_xs=xs, cdf_ps=ps, ubound=ubound)
                if upperbounded.candidate_is_feasible():
                    dist = upperbounded.candidate
                    break
            else:
                raise ValueError(f"Did not find a suitable upper bound for values {xs}.")

    return dist
