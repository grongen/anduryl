import sys
from pathlib import Path
from scipy import optimize
import bisect

import numpy as np

githubpath = Path("d:/Documents/GitHub/metalogistic")
if str(githubpath) not in sys.path:
    sys.path.append(str(githubpath))

import metalogistic

import pickle
from scipy.optimize import minimize

_JOIN_SIDES = False

def interpol(x1, x2, f1, f2, x):
    return f1 + (x - x1) / (x2 - x1) * (f2 - f1)


# class MetalogLoader:
#     def __init__(self):
#         self.Avalues_path = Path(__file__).parent / ".." / "data" / "_Avalues_metalog.pickle"
#         if self.Avalues_path.exists():
#             with self.Avalues_path.open("rb") as f:
#                 self._Avalues = pickle.load(f)
#         else:
#             self._Avalues = {}

#     def _save_Avalues(self):
#         with self.Avalues_path.open("wb") as f:
#             pickle.dump(self._Avalues, f)

#     def add_avector(self, savekey, avector):
#         print(len(savekey[1]), len(avector))
#         self._Avalues[savekey] = avector.tolist()
#         self._save_Avalues()

#     def load_metalog(self, savekey: tuple):
#         if savekey not in self._Avalues:
#             return None

#         else:
#             a_vector = self._Avalues[savekey]
#             print(len(savekey[1]), len(a_vector))
#             ps, xs, _, item_lbound, item_ubound = savekey
#             metalog = CustomMetaLogistic2(
#                 cdf_ps=ps, cdf_xs=xs, lbound=item_lbound, ubound=item_ubound, a_vector=np.array(a_vector)
#             )
#             return metalog


# MLLOADER = MetalogLoader()


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
        self.candidate = metalogistic.main._MetaLogisticMonoFit(**user_kwargs, fit_method="Linear least squares")

    def candidate_is_feasible(self) -> bool:
        """Determines if a candidate is feasible, by calculating a series of percentile
        points, and determining if the resulting cdf values are monotone.

        Returns:
            bool: Whether the candidate is feasible
        """
        eps = 0.001
        y = np.linspace(eps, 1 - eps, 100)
        x = self.candidate.ppf(q=y)
        return (x[1:] > x[:-1]).all()


from scipy.optimize import brentq


class BoundedMetalogFinder:
    def __init__(self, ps, xs, item_lbound=None, item_rbound=None):
        self.ps = ps
        self.xs = xs

        self.item_lbound = item_lbound
        self.item_ubound = item_rbound

        # Check if the skewness is towards the lower or upper end
        self.lower_interquantile = xs[1] - xs[0]
        self.upper_interquantile = xs[-1] - xs[-2]

        lower_dens = (ps[1] - ps[0]) / self.lower_interquantile
        upper_dens = (ps[-1] - ps[-2]) / self.upper_interquantile

        self.boundedness = "lb" if lower_dens > upper_dens else "ub"
        self.is_spt = 1 - self.ps[0] == self.ps[-1] and self.ps[1] == 0.5 and len(self.ps) == 3
        if self.is_spt:
            self.alpha = self.ps[0]

    def find(self):
        if self.is_spt and self.item_lbound is None and self.item_ubound is None:
            try:
                lims = self.solve_bounds()
            except:
                lims = self.iterate_bounds()
        else:
            lims = self.iterate_bounds()

        # Given the limits, find the metalog distribution with the lowest peak probability density
        return self.find_low_info_metalog(lims)

    def _med_low_LB(self, LB, LQ, UQ, alpha):
        term = 0.5 * (1 - 1.66711 * (0.5 - alpha))
        return LB + (LQ - LB) ** (1 - term) * (UQ - LB) ** term

    def _med_high_LB(self, LB, LQ, UQ, alpha):
        term = 0.5 * (1 - 1.66711 * (0.5 - alpha))
        return LB + (LQ - LB) ** term * (UQ - LB) ** (1 - term)

    def _med_low_UB(self, UB, LQ, UQ, alpha):
        term = 0.5 * (1 - 1.66711 * (0.5 - alpha))
        return UB - (UB - LQ) ** (1 - term) * (UB - UQ) ** term

    def _med_high_UB(self, UB, LQ, UQ, alpha):
        term = 0.5 * (1 - 1.66711 * (0.5 - alpha))
        return UB - (UB - LQ) ** term * (UB - UQ) ** (1 - term)

    def solve_bounds(self):
        med = self.xs[1]

        if self.boundedness == "lb":
            a = -1e10
            b = self.xs[0]
            lower_lim = brentq(f=lambda x: self._med_low_LB(x, self.xs[0], self.xs[-1], self.alpha) - med, a=a, b=b)
            upper_lim = brentq(f=lambda x: self._med_high_LB(x, self.xs[0], self.xs[-1], self.alpha) - med, a=a, b=b)
            if upper_lim == self.xs[0]:
                upper_lim -= (upper_lim - lower_lim) * 1e-3

        elif self.boundedness == "ub":
            a = 1e10
            b = self.xs[-1]
            lower_lim = brentq(f=lambda x: self._med_low_UB(x, self.xs[0], self.xs[-1], self.alpha) - med, a=a, b=b)
            upper_lim = brentq(f=lambda x: self._med_high_UB(x, self.xs[0], self.xs[-1], self.alpha) - med, a=a, b=b)
            if lower_lim == self.xs[-1]:
                lower_lim += (upper_lim - lower_lim) * 1e-3

        if lower_lim == upper_lim:
            raise ValueError('Equal bounds were found.')

        return lower_lim, upper_lim

    def iterate_bounds(self):
        steps = np.logspace(start=np.log10(1e-2), stop=np.log10(1e2), num=30)

        if self.boundedness == "lb":
            steps = self.xs[0] - (steps * self.lower_interquantile)
            for lbound in steps[::-1]:
                if not self.item_lbound is None and (lbound < self.item_lbound):
                    continue
                lowerbounded = CustomMetaLogistic2(cdf_xs=self.xs, cdf_ps=self.ps, lbound=lbound, term=3)
                if lowerbounded.is_feasible():
                    lower_lim = lbound
                    break
            else:
                raise ValueError(f"Did not find a suitable lower bound for values {self.xs}.")

            for lbound in steps:
                if not self.item_lbound is None and (lbound < self.item_lbound):
                    continue
                lowerbounded = CustomMetaLogistic2(cdf_xs=self.xs, cdf_ps=self.ps, lbound=lbound, term=3)
                if lowerbounded.is_feasible():
                    upper_lim = lbound
                    break
            else:
                raise ValueError(f"Did not find a suitable lower bound for values {self.xs}.")

        elif self.boundedness == "ub":
            steps = self.xs[-1] + (steps * self.upper_interquantile)
            for ubound in steps[::-1]:
                if not self.item_ubound is None and (ubound > self.item_ubound):
                    continue
                upperbounded = CustomMetaLogistic2(cdf_xs=self.xs, cdf_ps=self.ps, ubound=ubound, term=3)
                if upperbounded.is_feasible():
                    upper_lim = ubound
                    break
            else:
                raise ValueError(f"Did not find a suitable upper bound for values {self.xs}.")

            for ubound in steps:
                if not self.item_ubound is None and (ubound > self.item_ubound):
                    continue
                upperbounded = CustomMetaLogistic2(cdf_xs=self.xs, cdf_ps=self.ps, ubound=ubound, term=3)
                if upperbounded.is_feasible():
                    lower_lim = ubound
                    break
            else:
                raise ValueError(f"Did not find a suitable upper bound for values {self.xs}.")

        return lower_lim, upper_lim

    def find_low_info_metalog(self, lims):
        def get_max_density(bound):
            disc = np.linspace(1e-5, 1 - 1e-5, 201)
            if self.boundedness == "lb":
                dist = CustomMetaLogistic2(
                    cdf_xs=self.xs, cdf_ps=self.ps, lbound=bound, ubound=self.item_ubound, term=3
                )
            elif self.boundedness == "ub":
                dist = CustomMetaLogistic2(
                    cdf_xs=self.xs, cdf_ps=self.ps, lbound=self.item_lbound, ubound=bound, term=3
                )
            # Calculate the values at the percentile points
            cdvals = dist.ppf(disc)
            # The minimum distance in between those values indicates the highest probability density
            # (assuming the numerical discretization is fine enough)
            density_measure = (cdvals[1:] - cdvals[:-1]).min()
            # The function is used to find the least informative, lowest max density function using minimization.
            # Therefore, return the negative measure for highest prob dens (min distance), such that the lowest is returnes
            return -density_measure
        
        lim_min_info = minimize(get_max_density, x0=(np.mean(lims),), bounds=(lims,)).x[0]

        if self.boundedness == "lb":
            bounded = CustomMetaLogistic2(
                cdf_xs=self.xs, cdf_ps=self.ps, term=3, lbound=lim_min_info, ubound=self.item_ubound
            )
        elif self.boundedness == "ub":
            bounded = CustomMetaLogistic2(
                cdf_xs=self.xs, cdf_ps=self.ps, term=3, ubound=lim_min_info, lbound=self.item_lbound
            )

        return bounded

    # Precalculate some percentile point values
    # dist.set_interpolation_cdf(get_tail_dense_discretization())


def get_valid_metalog(ps, xs, item_lbound=None, item_ubound=None):
    # Check if the unbounded candidate is feasible
    unbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=3, lbound=item_lbound, ubound=item_ubound)
    if unbounded.is_feasible():
        dist = unbounded

    else:
        dist = BoundedMetalogFinder(ps, xs).find()

    # Precalculate some percentile point values
    dist.set_interpolation_cdf(get_tail_dense_discretization())

    return dist


def get_tail_dense_discretization(tailp=0.02, minp=1e-5, nlin=251, ntail=20):
    tailp = 0.02
    # Generate a linear spaced range from tailp to 1 - tailp
    linspaced = np.linspace(tailp, 1.0 - tailp, nlin)[1:-1]
    # Add a logspaced part at the tails
    logspaced = np.logspace(np.log10(tailp), np.log10(minp), ntail, base=10)

    return np.concatenate([logspaced[::-1], linspaced, 1 - logspaced])


def get_valid_5p_metalog(ps, xs, item_lbound=None, item_ubound=None, method="2part_3p"):
    # Check if the unbounded candidate is feasible
    unbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, lbound=item_lbound, ubound=item_ubound)
    if unbounded.is_feasible():
        dist = unbounded

    else:
        if method == "bounding":
            dist = get_5p_metalog_by_bounding()
            # Did not work, get a 3p metalog
            if dist is None:
                dist = get_valid_metalog(xs=xs, ps=ps, lbound=item_lbound, ubound=item_ubound)

        elif method == "2part_3p":
            dist = get_2part_3p_metalog(xs=xs, ps=ps, lbound=item_lbound, ubound=item_ubound, join_sides=_JOIN_SIDES)

        else:
            raise NotImplementedError(method)

    return dist


def get_2part_3p_metalog(ps, xs, lbound=None, ubound=None, join_sides=True):
    left_ps = ps[:3]
    left_xs = xs[:3]
    right_ps = ps[-3:]
    right_xs = xs[-3:]

    # Get a valid metalog for the first three and last three percentiles
    left_dist = get_valid_metalog(left_ps, left_xs, item_lbound=lbound, item_ubound=ubound)
    right_dist = get_valid_metalog(right_ps, right_xs, item_lbound=lbound, item_ubound=ubound)
    unjoined = CombinedMetaLogistic(left_dist, right_dist)

    if not join_sides:
        # If not join sides, return the 2 parts with a step at the midpoint
        return unjoined

    # If join_sides, try to match the probability density at the midpoint
    midpoint = left_dist.cdf_xs[-1]
    p_left = left_dist.pdf(midpoint)
    p_right = right_dist.pdf(midpoint)

    # print(left_dist.ppf(0.5), right_dist.ppf(0.5), p_left, p_right)

    # If left pdf is higher than right, increase pdf right at midpoint by shifting left bound to right
    if p_left > p_right:

        def func(bound):
            right_dist_tst = CustomMetaLogistic2(cdf_ps=right_ps, cdf_xs=right_xs, lbound=bound, ubound=ubound)
            p_right_tst = right_dist_tst.pdf(midpoint) if right_dist_tst.is_feasible() else p_left * 2
            return p_right_tst - p_left

        # Define a very wide range for the bounds
        a = right_dist.ppf(0.00001)
        b = right_dist.ppf(0.49999)

        xs_mid = right_dist.ppf(0.5)
        # Only do the optimization if this range is large enough. If not just use the original right side distribuation
        try:
            if np.sign(func(a)) != np.sign(func(b)):
                opt_bound = optimize.brentq(func, a, b)
                if np.isclose(right_dist.ppf(0.5), xs_mid):
                        right_dist = get_valid_metalog(right_ps, right_xs, item_lbound=opt_bound, item_ubound=ubound)
        except:
            pass

    elif p_left < p_right:

        def func(bound):
            left_dist_tst = CustomMetaLogistic2(cdf_ps=left_ps, cdf_xs=left_xs, lbound=lbound, ubound=bound)
            p_left_tst = left_dist_tst.pdf(midpoint) if left_dist_tst.is_feasible() else p_right * 2
            return p_left_tst - p_right

        a = left_dist.ppf(0.99999)
        b = left_dist.ppf(0.50001)

        xs_mid = left_dist.ppf(0.5)
        try:
            if np.sign(func(a)) != np.sign(func(b)):
                opt_bound = optimize.brentq(func, a, b)
                if np.isclose(left_dist.ppf(0.5), xs_mid):
                        left_dist = get_valid_metalog(left_ps, left_xs, item_lbound=lbound, item_ubound=opt_bound)
        except:
            pass
    try:
        return CombinedMetaLogistic(left_dist, right_dist)
    except:
        return unjoined


def get_5p_metalog_by_bounding(ps, xs, item_lbound=None, item_ubound=None, method="bounding"):
    if not item_ubound is None:
        raise NotImplementedError()
    if not item_lbound is None:
        raise NotImplementedError()

    for f in [10, 1, 0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001]:
        dist = xs[-1] - xs[0]
        lbound = xs[0] - (xs[1] - xs[0]) * f
        ubound = xs[-1] + (xs[-1] - xs[-2]) * f
        dist = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=5, lbound=lbound, ubound=ubound)
        if dist.is_feasible():
            break
    else:
        return None

    # Try to extend the bounds
    # Lower bound
    if CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=5, ubound=ubound).is_feasible():
        lbound = None
    else:
        steps = np.logspace(start=np.log10(1e-2), stop=np.log10(1e2), num=30)
        steps = xs[0] - (steps * (xs[1] - xs[0]))
        for incr_lbound in steps[::-1]:
            lowerbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, lbound=incr_lbound, ubound=ubound)
            if lowerbounded.is_feasible():
                lbound = incr_lbound
                break

    # Upper bound
    if CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=5, lbound=lbound).is_feasible():
        ubound = None
    else:
        steps = np.logspace(start=np.log10(1e-2), stop=np.log10(1e2), num=30)
        steps = xs[-1] + (steps * (xs[-1] - xs[-2]))
        for incr_ubound in steps[::-1]:
            upperbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, lbound=lbound, ubound=incr_ubound)
            if upperbounded.is_feasible():
                ubound = incr_ubound
                break

    dist = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=5, lbound=lbound, ubound=ubound)

    return dist


def is_list_like(object):
    return isinstance(object, list) or (isinstance(object, np.ndarray) and object.ndim == 1)


def is_numeric(object):
    return isinstance(object, (float, int, np.int32, np.int64)) or (
        isinstance(object, np.ndarray) and object.ndim == 0
    )


class CustomMetaLogistic2:
    """
    This class should generally only be called inside its user-facing subclass MetaLogistic.

    It attempts to fit the data using only one fit method and one number of terms. The other class,
    MetaLogistic, handles the logic for attempting multiple fit methods.

    Here, we subclass scipy.stats.rv_continuous so we can make use of all the nice SciPy methods. We redefine the private methods
    _cdf, _pdf, and _ppf, and SciPy will make calls to these whenever needed.
    """

    def __init__(
        self,
        cdf_ps=None,
        cdf_xs=None,
        term=None,
        lbound=None,
        ubound=None,
        a_vector=None,
    ):
        """
        This class should only be called inside its user-facing subclass MetaLogistic.
        """
        if lbound == -np.inf:
            print("Infinite lower bound was ignored")
            lbound = None

        if ubound == np.inf:
            print("Infinite upper bound was ignored")
            ubound = None

        if lbound is None and ubound is None:
            self.boundedness = False
        if lbound is None and ubound is not None:
            self.boundedness = "upper"
            self.a, self.b = -np.inf, ubound
        if lbound is not None and ubound is None:
            self.boundedness = "lower"
            self.a, self.b = lbound, np.inf
        if lbound is not None and ubound is not None:
            self.boundedness = "bounded"
            self.a, self.b = lbound, ubound
        self.lbound = lbound
        self.ubound = ubound

        self.cdf_ps = cdf_ps
        self.cdf_xs = cdf_xs
        if cdf_xs is not None and cdf_ps is not None:
            self.cdf_len = len(cdf_ps)
            self.cdf_ps = np.asarray(self.cdf_ps)
            self.cdf_xs = np.asarray(self.cdf_xs)

        if term is None:
            self.term = self.cdf_len
        else:
            self.term = term

        # Special case where a MetaLogistic object is created by supplying the a-vector directly.
        if a_vector is not None:
            self.a_vector = a_vector
            # The metalog calculates a pdf iteratively. For speed up, prepare interpolated pdf points
            self.set_interpolation_cdf(get_tail_dense_discretization())
            if term is None:
                self.term = len(a_vector)
            else:
                self.term = term

        else:
            # if not, derive the Metalogistic by least squares fitting
            self.fit_linear_least_squares()

        self._pps = None
        self._prange = None

        # Create empty list for quantiles and cumulative probabilities that are already calculated
        self._quantiles = []
        self._cumulative_probs = []

    def _add_quantile(self, quantile, probability):
        pos = bisect.bisect(self._quantiles, quantile)
        if probability in self._cumulative_probs:
            return None
        self._quantiles.insert(pos, quantile)
        self._cumulative_probs.insert(pos, probability)

    def is_feasible(self, eps=0.001, npts=500) -> bool:
        """Determines if a candidate is feasible, by calculating a series of percentile
        points, and determining if the resulting cdf values are monotone.

        Returns:
            bool: Whether the candidate is feasible
        """
        if self.term == 3:
            # Check analytically
            analytical_condition = self.a_vector[1] > 0 and abs(self.a_vector[2]) / self.a_vector[1] < 1.66711
            return analytical_condition
        else:
            # Check numerically
            y = get_tail_dense_discretization()
            x = self.ppf(probability=y)
            feasible = (x[1:] > x[:-1]).all()
            return feasible

    @property
    def pps(self):
        if self._pps is None:
            self.set_interpolation_cdf(self.prange)
        return self._pps

    @property
    def prange(self):
        if self._prange is None:
            self._prange = get_tail_dense_discretization()
        return self._prange

    def set_interpolation_cdf(self, prange):
        self._prange = prange
        self._pps = np.array(self.ppf(prange))

        diff = self._pps[1:] - self._pps[:-1]
        if any(diff < 0):
            raise ValueError("Infeasible distribution")

    def fit_linear_least_squares(self):
        """
        Constructs the a-vector by linear least squares, as defined in Keelin 2016, Equation 7 (unbounded case), Equation 12 (semi-bounded and bounded cases).
        """
        z_vec = self._construct_z_vec()
        Y_matrix = self._construct_y_matrix()

        left = np.linalg.inv(np.dot(Y_matrix.T, Y_matrix))
        right = np.dot(Y_matrix.T, z_vec)

        self.a_vector = np.dot(left, right)

    def quantile_slope_numeric(self, p):
        """
        Gets the slope of the quantile function by simple finite-difference approximation.
        """
        epsilon = 1e-5
        if not np.isfinite(self.quantile(p + epsilon)):
            epsilon = -epsilon
        cdf_slope = optimize.approx_fprime(p, self.quantile, epsilon)
        return cdf_slope

    def quantile_minimum_increment(self):
        """
        Nice idea but in practise the worst feasibility method, I might remove it.
        """
        # Get a good initial guess
        check_ps_from = 0.001
        number_to_check = 100
        ps_to_check = np.linspace(check_ps_from, 1 - check_ps_from, number_to_check)
        xs = self.quantile(ps_to_check)
        xs_diff = np.diff(xs)
        i = np.argmin(xs_diff)
        p0 = ps_to_check[i]

        # Do the minimization
        r = optimize.minimize(self.quantile_slope_numeric, x0=p0, bounds=[(0, 1)])
        return r.fun

    def _construct_z_vec(self):
        """
        Constructs the z-vector, as defined in Keelin 2016, Section 3.3 (unbounded case, where it is called the `x`-vector),
        Section 4.1 (semi-bounded case), and Section 4.3 (bounded case).

        This vector is a transformation of cdf_xs to account for bounded or semi-bounded distributions.
        When the distribution is unbounded, the z-vector is simply equal to cdf_xs.
        """
        if not self.boundedness:
            z_vec = self.cdf_xs
        if self.boundedness == "lower":
            z_vec = np.log(self.cdf_xs - self.lbound)
        if self.boundedness == "upper":
            z_vec = -np.log(self.ubound - self.cdf_xs)
        if self.boundedness == "bounded":
            z_vec = np.log((self.cdf_xs - self.lbound) / (self.ubound - self.cdf_xs))

        return z_vec

    def _construct_y_matrix(self):
        """
        Constructs the Y-matrix, as defined in Keelin 2016, Equation 8.
        """

        # The series of Y_n matrices. Although we only use the last matrix in the series, the entire series is necessary to construct it
        Y_ns = {}
        ones = np.ones(self.cdf_len).reshape(self.cdf_len, 1)
        column_2 = np.log(self.cdf_ps / (1 - self.cdf_ps)).reshape(self.cdf_len, 1)
        column_4 = (self.cdf_ps - 0.5).reshape(self.cdf_len, 1)
        Y_ns[2] = np.hstack([ones, column_2])
        Y_ns[3] = np.hstack([Y_ns[2], column_4 * column_2])
        Y_ns[4] = np.hstack([Y_ns[3], column_4])

        if self.term > 4:
            for n in range(5, self.term + 1):
                if n % 2 != 0:
                    new_column = column_4 ** ((n - 1) / 2)
                    Y_ns[n] = np.hstack([Y_ns[n - 1], new_column])

                if n % 2 == 0:
                    new_column = (column_4 ** (n / 2 - 1)) * column_2
                    Y_ns[n] = np.hstack([Y_ns[n - 1], new_column])

        Y_matrix = Y_ns[self.term]

        return Y_matrix

    def quantile(self, probability, force_unbounded=False):
        """
        The metalog inverse CDF, or quantile function, as defined in Keelin 2016, Equation 6 (unbounded case), Equation 11 (semi-bounded case),
        and Equation 14 (bounded case).

        `probability` must be a scalar.
        """

        # if not 0 <= probability <= 1:
        # 	raise ValueError("Probability in call to quantile() must be between 0 and 1")

        if is_list_like(probability):
            return self.quantile_arr(probability, force_unbounded=force_unbounded)

        if probability <= 0:
            if (self.boundedness == "lower" or self.boundedness == "bounded") and not force_unbounded:
                return self.lbound
            else:
                return -np.inf

        elif probability >= 1:
            if (self.boundedness == "upper" or self.boundedness == "bounded") and not force_unbounded:
                return self.ubound
            else:
                return np.inf

        # `self.a_vector` is 0-indexed, while in Keelin 2016 the a-vector is 1-indexed.
        # To make this method as easy as possible to read if following along with the paper, I create a dictionary `a`
        # that mimics a 1-indexed vector.
        # a = {i + 1: element for i, element in enumerate(self.a_vector)}
        base1 = 1
        a = self.a_vector

        # The series of quantile functions. Although we only return the last result in the series, the entire series is necessary to construct it
        ln_p_term = np.log(probability / (1 - probability))
        p05_term = probability - 0.5
        quantile_functions = {2: a[1 - base1] + a[2 - base1] * ln_p_term}

        if self.term > 2:
            quantile_functions[3] = quantile_functions[2] + a[3 - base1] * p05_term * ln_p_term
        if self.term > 3:
            quantile_functions[4] = quantile_functions[3] + a[4 - base1] * p05_term

        if self.term > 4:
            for n in range(5, self.term + 1):
                if n % 2 != 0:
                    quantile_functions[n] = quantile_functions[n - 1] + a[n - base1] * p05_term ** ((n - 1) / 2)

                if n % 2 == 0:
                    quantile_functions[n] = (
                        quantile_functions[n - 1] + a[n - base1] * p05_term ** (n / 2 - 1) * ln_p_term
                    )

        quantile_function = quantile_functions[self.term]

        if not force_unbounded:
            if self.boundedness == "lower":
                quantile_function = self.lbound + np.exp(quantile_function)  # Equation 11
            elif self.boundedness == "upper":
                quantile_function = self.ubound - np.exp(-quantile_function)
            elif self.boundedness == "bounded":
                quantile_function = (self.lbound + self.ubound * np.exp(quantile_function)) / (
                    1 + np.exp(quantile_function)
                )  # Equation 14

        self._add_quantile(quantile_function, probability)

        return quantile_function

    def quantile_arr(self, probability, force_unbounded):
        quantile_function = np.zeros_like(probability)

        idx_le0 = probability <= 0
        if idx_le0.any():
            if (self.boundedness == "lower" or self.boundedness == "bounded") and not force_unbounded:
                quantile_function[idx_le0] = self.lbound
            else:
                quantile_function[idx_le0] - np.inf

        idx_ge0 = probability >= 1
        if idx_ge0.any():
            if (self.boundedness == "upper" or self.boundedness == "bounded") and not force_unbounded:
                quantile_function[idx_ge0] = self.ubound
            else:
                quantile_function[idx_ge0] = np.inf

        idx_rem = ~(idx_ge0 | idx_le0)
        probability = probability[idx_rem].copy()

        # `self.a_vector` is 0-indexed, while in Keelin 2016 the a-vector is 1-indexed.
        # To make this method as easy as possible to read if following along with the paper, I create a dictionary `a`
        # that mimics a 1-indexed vector.
        a = {i + 1: element for i, element in enumerate(self.a_vector)}

        # The series of quantile functions. Although we only return the last result in the series, the entire series is necessary to construct it
        ln_p_term = np.log(probability / (1 - probability))
        p05_term = probability - 0.5
        quantile_functions = {2: a[1] + a[2] * ln_p_term}

        if self.term > 2:
            quantile_functions[3] = quantile_functions[2] + a[3] * p05_term * ln_p_term
        if self.term > 3:
            quantile_functions[4] = quantile_functions[3] + a[4] * p05_term

        if self.term > 4:
            for n in range(5, self.term + 1):
                if n % 2 != 0:
                    quantile_functions[n] = quantile_functions[n - 1] + a[n] * p05_term ** ((n - 1) / 2)

                if n % 2 == 0:
                    quantile_functions[n] = quantile_functions[n - 1] + a[n] * p05_term ** (n / 2 - 1) * ln_p_term

        quantile_function[idx_rem] = quantile_functions[self.term]

        if not force_unbounded:
            if self.boundedness == "lower":
                quantile_function[idx_rem] = self.lbound + np.exp(quantile_function[idx_rem])  # Equation 11
            elif self.boundedness == "upper":
                quantile_function[idx_rem] = self.ubound - np.exp(-quantile_function[idx_rem])
            elif self.boundedness == "bounded":
                quantile_function[idx_rem] = (self.lbound + self.ubound * np.exp(quantile_function[idx_rem])) / (
                    1 + np.exp(quantile_function[idx_rem])
                )  # Equation 14

        for quant, prob in zip(quantile_function, probability):
            self._add_quantile(quant, prob)

        return quantile_function

    def density_m(self, cumulative_prob, force_unbounded=False):
        """
        This is the metalog PDF as a function of cumulative probability, as defined in Keelin 2016, Equation 9 (unbounded case),
        Equation 13 (semi-bounded case), Equation 15 (bounded case).

        Notice the unusual definition of the PDF, which is why I call this function density_m in reference to the notation in
        Keelin 2016.
        """

        if is_list_like(cumulative_prob):
            return np.asarray([self.density_m(i) for i in cumulative_prob])

        if not 0 <= cumulative_prob <= 1:
            raise ValueError("Probability in call to density_m() must be between 0 and 1")
        if not self.boundedness and (cumulative_prob == 0 or cumulative_prob == 1):
            raise ValueError(
                "Probability in call to density_m() cannot be equal to 0 and 1 for an unbounded distribution"
            )

        # The series of density functions. Although we only return the last result in the series, the entire series is necessary to construct it
        density_functions = {}

        # `self.a_vector` is 0-indexed, while in Keelin 2016 the a-vector is 1-indexed.
        # To make this method as easy as possible to read if following along with the paper, I create a dictionary `a`
        # that mimics a 1-indexed vector.
        a = {i + 1: element for i, element in enumerate(self.a_vector)}

        if cumulative_prob == 0.0 or cumulative_prob == 1.0:
            return 0.0

        ln_p_term = np.log(cumulative_prob / (1 - cumulative_prob))
        p05_term = cumulative_prob - 0.5
        p1p_term = cumulative_prob * (1 - cumulative_prob)

        density_functions[2] = p1p_term / a[2]
        if self.term > 2:
            density_functions[3] = 1 / (1 / density_functions[2] + a[3] * (p05_term / p1p_term + ln_p_term))
        if self.term > 3:
            density_functions[4] = 1 / (1 / density_functions[3] + a[4])

        if self.term > 4:
            for n in range(5, self.term + 1):
                if n % 2 != 0:
                    density_functions[n] = 1 / (
                        1 / density_functions[n - 1] + a[n] * ((n - 1) / 2) * p05_term ** ((n - 3) / 2)
                    )

                if n % 2 == 0:
                    density_functions[n] = 1 / (
                        1 / density_functions[n - 1]
                        + a[n]
                        * (p05_term ** (n / 2 - 1) / p1p_term + (n / 2 - 1) * p05_term ** (n / 2 - 2) * ln_p_term)
                    )

        density_function = density_functions[self.term]
        if not force_unbounded:
            if self.boundedness == "lower":  # Equation 13
                if 0 < cumulative_prob < 1:
                    density_function = density_function * np.exp(-self.quantile(cumulative_prob, force_unbounded=True))
                elif cumulative_prob == 0:
                    density_function = 0
                else:
                    raise ValueError(
                        "Probability in call to density_m() cannot be equal to 1 with a lower-bounded distribution."
                    )

            elif self.boundedness == "upper":
                if 0 < cumulative_prob < 1:
                    density_function = density_function * np.exp(self.quantile(cumulative_prob, force_unbounded=True))
                elif cumulative_prob == 1:
                    density_function = 0
                else:
                    raise ValueError(
                        "Probability in call to density_m() cannot be equal to 0 with a upper-bounded distribution."
                    )

            elif self.boundedness == "bounded":  # Equation 15
                if 0 < cumulative_prob < 1:
                    x_unbounded = np.exp(self.quantile(cumulative_prob, force_unbounded=True))
                    density_function = (
                        density_function * (1 + x_unbounded) ** 2 / ((self.ubound - self.lbound) * x_unbounded)
                    )
                if cumulative_prob == 0 or cumulative_prob == 1:
                    density_function = 0

        return density_function

    def get_cumulative_prob(self, x, lowerbound=0.0, upperbound=1.0, interp_tol=None):
        """
        The metalog is defined in terms of its inverse CDF or quantile function. In order to get probabilities for a given x-value,
        like in a traditional CDF, we invert this quantile function using a numerical equation solver.

        `x` must be a scalar
        """
        if self.lbound is not None and x <= self.lbound:
            return 0.0
        elif self.ubound is not None and x >= self.ubound:
            return 1.0

        f_to_zero = lambda probability: self.quantile(probability) - x

        # We need a smaller `xtol` than the default value, in order to ensure correctness when
        # evaluating the CDF or PDF in the extreme tails.
        xtol = 1e-24
        # todo: consider replacing brent's method with Newton's (or other), and provide the derivative of quantile, since it should be possible to obtain an analytic expression for that

        if self._quantiles:
            if x in self._quantiles:
                return self._cumulative_probs[self._quantiles.index(x)]
            # Get the position of the the new value in the quantiles
            pos = bisect.bisect(self._quantiles, x)
            # Adjust lower bound based on percentiles that were already calculated
            if x > self._quantiles[0]:
                lowerbound = self._cumulative_probs[pos - 1]
            if x < self._quantiles[-1]:
                upperbound = self._cumulative_probs[pos]

            # # If the difference is between a certain tolerance, interpolate
            # if interp_tol is not None and (upperbound - lowerbound) < interp_tol and (pos > 0 and pos < len(self._quantiles)):
            #     return interpol(x1=self._quantiles[pos-1], x2=self._quantiles[pos], f1=lowerbound, f2=upperbound, x=x)

            # Adjust the tolerance based on the surrounding probabilities
            # xtol = max(xtol, min(lowerbound, upperbound) * 1e-6)

        return optimize.brentq(f_to_zero, lowerbound, upperbound, xtol=xtol, disp=True)

    def cdf(self, x, interp_tol=None):
        """
        This is where we override the SciPy method for the CDF.

        `x` may be a scalar or list-like.
        """
        if is_list_like(x):
            return [self.cdf(i, interp_tol=interp_tol) for i in x]
        if is_numeric(x):
            return self.get_cumulative_prob(x, interp_tol=interp_tol)

    def ppf(self, probability, interp_tol=None):
        """
        This is where we override the SciPy method for the inverse CDF or quantile function (ppf stands for percent point function).

        `probability` may be a scalar or list-like.
        """
        return self.quantile(probability)

    def pdf(self, x):
        """
        This is where we override the SciPy method for the PDF.

        `x` may be a scalar or list-like.
        """
        if is_list_like(x):
            return [self.pdf(i) for i in x]

        if is_numeric(x):
            cumulative_prob = self.get_cumulative_prob(x)
            return self.density_m(cumulative_prob)

    def plot(self, axs=None):
        import matplotlib.pyplot as plt

        if axs is None:
            fig, _axs = plt.subplots(nrows=2)
        else:
            _axs = axs
        ax = _axs[0]
        ax.plot(self.pps, self.prange)
        for ix in self.cdf_xs:
            ax.axvline(ix, color="k", lw=0.75, ls=":", label=ix)

        ax = _axs[1]
        ax.plot(self.pps, np.gradient(self.prange, self.pps))
        for ix in self.cdf_xs:
            ax.axvline(ix, color="k", lw=0.75, ls=":", label=ix)

        ax.legend()

        if axs is None:
            plt.show()


class CombinedMetaLogistic(CustomMetaLogistic2):
    def __init__(self, dist_l, dist_r):
        self.dist_l = dist_l
        self.dist_r = dist_r

        assert self.dist_l.cdf_xs[-1] == self.dist_r.cdf_xs[0]
        self.midpoint = self.dist_l.cdf_xs[-1]

        self._pps = None
        self._prange = None

        self.set_interpolation_cdf = super().set_interpolation_cdf

        if ((self.pps[1:] - self.pps[:-1]) <= 0).any():
            # import matplotlib.pyplot as plt
            # fig, axs = plt.subplots(ncols=2)
            # self.dist_l.plot(axs=axs)
            # self.dist_r.plot(axs=axs)
            # plt.show()
            raise ValueError("Percentile points not monotincally increasing")

    def _exec_func_lr(self, func, x, interp_tol=None, split=0.5):
        """Method that determines whether a function is called from the left or right distribution"""
        func_l = getattr(self.dist_l, func)
        func_r = getattr(self.dist_r, func)

        return np.where(x < split, func_l(x, interp_tol), func_r(x, interp_tol))

    def pdf(self, x, interp_tol=None):
        return self._exec_func_lr("pdf", x, interp_tol, split=self.midpoint)

    def cdf(self, x, interp_tol=None):
        return self._exec_func_lr("cdf", x, interp_tol, split=self.midpoint)

    def ppf(self, probability):
        return self._exec_func_lr("ppf", probability, split=0.5)

    def plot(self):
        import matplotlib.pyplot as plt

        fig, axs = plt.subplots(nrows=2)
        self.dist_l.plot(axs)
        self.dist_r.plot(axs)
        axs[0].plot(self.pps, self.prange, 1, color="k", ls="--")
        axs[1].plot(self.pps, np.gradient(self.prange, self.pps), lw=1, color="k", ls="--")

        plt.show()
