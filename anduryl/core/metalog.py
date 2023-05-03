from multiprocessing.sharedctypes import Value
import sys
from pathlib import Path
from scipy import optimize

import numpy as np

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
        y = np.linspace(eps, 1 - eps, 100)
        x = self.candidate.ppf(q=y)
        return (x[1:] > x[:-1]).all()


def get_valid_metalog(ps, xs, item_lbound=None, item_ubound=None):
    # Check if the unbounded candidate is feasible
    unbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=3, lbound=item_lbound, ubound=item_ubound)
    if unbounded.is_feasible():
        dist = unbounded

    else:

        # Check if the skewness is towards the lower or upper end
        lower_interquantile = xs[1] - xs[0]
        upper_interquantile = xs[-1] - xs[-2]
        steps = np.logspace(start=np.log10(1e-2), stop=np.log10(1e2), num=30)

        if lower_interquantile < upper_interquantile:
            steps = xs[0] - (steps * lower_interquantile)
            for lbound in steps[::-1]:
                if not np.isnan(item_lbound) and (lbound < item_lbound):
                    continue
                lowerbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, lbound=lbound, term=3)
                if lowerbounded.is_feasible():
                    dist = lowerbounded
                    break
            else:
                raise ValueError(f"Did not find a suitable lower bound for values {xs}.")

        else:
            steps = xs[-1] + (steps * upper_interquantile)
            for ubound in steps[::-1]:
                if not np.isnan(item_ubound) and (ubound > item_ubound):
                    continue
                upperbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, ubound=ubound, term=3)
                if upperbounded.is_feasible():
                    dist = upperbounded
                    break
            else:
                raise ValueError(f"Did not find a suitable upper bound for values {xs}.")

    # Precalculate some percentile point values
    tailp = 0.02
    linspaced = np.linspace(tailp, 1.0 - tailp, 101)[1:-1]
    logspaced = np.logspace(np.log10(tailp), np.log10(1e-5), 10, base=10)
    dist.prange = np.concatenate([logspaced[::-1], linspaced, 1 - logspaced])
    dist.pps = dist.ppf(dist.prange)

    return dist


def get_valid_5p_metalog(ps, xs, item_lbound=None, item_ubound=None):
    if not np.isnan(item_ubound):
        raise NotImplementedError()
    if not np.isnan(item_lbound):
        raise NotImplementedError()
    # Check if the unbounded candidate is feasible
    unbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps)
    if unbounded.is_feasible():
        dist = unbounded

    else:

        # Try to fit the quadratic extrapolated 5p fit
        # from scipy.interpolate import interp1d

        # lbound, ubound = interp1d(ps, xs, fill_value="extrapolate", kind="cubic")([0.0, 1.0])
        # print(lbound, ubound)

        for f in [1, 0.1, 0.01, 0.001, 0.0001, 0.00001]:
            dist = xs[-1] - xs[0]
            lbound = xs[0] - (xs[1] - xs[0]) * f
            ubound = xs[-1] + (xs[-1] - xs[-2]) * f
            dist = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=5, lbound=lbound, ubound=ubound)
            if dist.is_feasible():
                break
        else:
            return get_valid_metalog(xs=xs, ps=ps)
            # raise ValueError(xs)

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

    # Precalculate some percentile point values
    tailp = 0.02
    linspaced = np.linspace(tailp, 1.0 - tailp, 101)[1:-1]
    logspaced = np.logspace(np.log10(tailp), np.log10(1e-5), 10, base=10)
    dist.prange = np.concatenate([logspaced[::-1], linspaced, 1 - logspaced])
    dist.pps = dist.ppf(dist.prange)

    return dist

    # # First, create a 3-term fit
    # dist = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=3)
    # # Get the difference in probability
    # pdiff = dist.cdf(xs) - np.array(ps)

    # def get_feasibility(dist):
    #     return ((dist.cdf(xs) - np.array(ps)) ** 2).sum()  # + int(not dist.is_feasible()) * 100

    # # If the line underceeds the highest point, and superseeds the one before
    # if pdiff[-1] < 0 and pdiff[-2] > 0:
    #     # Decrease upper bound
    #     x_p999 = dist.ppf(0.999)
    #     ubounds = np.linspace(x_p999, xs[-1], 100, endpoint=False)
    #     imin = np.argmin(
    #         [
    #             get_feasibility(CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, term=3, ubound=ubound))
    #             for ubound in ubounds
    #         ]
    #     )
    #     ubound = ubounds[imin]

    # Shift bounds to improve fit

    # Increase terms to 5

    # Shift bounds away while preserving feasibility

    # # Check if the skewness is towards the lower or upper end
    # lower_interquantile = xs[1] - xs[0]
    # upper_interquantile = xs[-1] - xs[-2]
    # steps = np.logspace(start=np.log10(1e-2), stop=np.log10(1e2), num=30)

    # if lower_interquantile < upper_interquantile:
    #     steps = xs[0] - (steps * lower_interquantile)
    #     for lbound in steps[::-1]:
    #         lowerbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, lbound=lbound)
    #         if lowerbounded.is_feasible():
    #             dist = lowerbounded
    #             break
    #     else:
    #         raise ValueError(f"Did not find a suitable lower bound for values {xs}.")

    # else:
    #     steps = xs[-1] + (steps * upper_interquantile)
    #     for ubound in steps[::-1]:
    #         upperbounded = CustomMetaLogistic2(cdf_xs=xs, cdf_ps=ps, ubound=ubound)
    #         if upperbounded.is_feasible():
    #             dist = upperbounded
    #             break
    #     else:
    #         raise ValueError(f"Did not find a suitable upper bound for values {xs}.")

    # Precalculate some percentile point values
    dist.prange = np.concatenate([[0.001], np.linspace(0.0, 1.0, 101)[1:-1], [0.999]])
    dist.pps = dist.ppf(dist.prange)

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

        # Special case where a MetaLogistic object is created by supplying the a-vector directly.
        if a_vector is not None:
            self.a_vector = a_vector
            if term is None:
                self.term = len(a_vector)
            else:
                self.term = term
            return

        if term is None:
            self.term = self.cdf_len
        else:
            self.term = term

        self.construct_z_vec()
        self.construct_y_matrix()

        self.fit_linear_least_squares()

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
            y = np.linspace(eps, 1 - eps, npts)
            x = self.ppf(probability=y)
            feasible = (x[1:] > x[:-1]).all()
            return feasible

    def fit_linear_least_squares(self):
        """
        Constructs the a-vector by linear least squares, as defined in Keelin 2016, Equation 7 (unbounded case), Equation 12 (semi-bounded and bounded cases).
        """
        left = np.linalg.inv(np.dot(self.Y_matrix.T, self.Y_matrix))
        right = np.dot(self.Y_matrix.T, self.z_vec)

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

    def construct_z_vec(self):
        """
        Constructs the z-vector, as defined in Keelin 2016, Section 3.3 (unbounded case, where it is called the `x`-vector),
        Section 4.1 (semi-bounded case), and Section 4.3 (bounded case).

        This vector is a transformation of cdf_xs to account for bounded or semi-bounded distributions.
        When the distribution is unbounded, the z-vector is simply equal to cdf_xs.
        """
        if not self.boundedness:
            self.z_vec = self.cdf_xs
        if self.boundedness == "lower":
            self.z_vec = np.log(self.cdf_xs - self.lbound)
        if self.boundedness == "upper":
            self.z_vec = -np.log(self.ubound - self.cdf_xs)
        if self.boundedness == "bounded":
            self.z_vec = np.log((self.cdf_xs - self.lbound) / (self.ubound - self.cdf_xs))

    def construct_y_matrix(self):
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

        self.Y_matrix = Y_ns[self.term]

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
                    quantile_functions[n] = (
                        quantile_functions[n - 1] + a[n] * p05_term ** (n / 2 - 1) * ln_p_term
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
                    quantile_functions[n] = (
                        quantile_functions[n - 1] + a[n] * p05_term ** (n / 2 - 1) * ln_p_term
                    )

        quantile_function[idx_rem] = quantile_functions[self.term]

        if not force_unbounded:
            if self.boundedness == "lower":
                quantile_function[idx_rem] = self.lbound + np.exp(quantile_function[idx_rem])  # Equation 11
            elif self.boundedness == "upper":
                quantile_function[idx_rem] = self.ubound - np.exp(-quantile_function[idx_rem])
            elif self.boundedness == "bounded":
                quantile_function[idx_rem] = (
                    self.lbound + self.ubound * np.exp(quantile_function[idx_rem])
                ) / (
                    1 + np.exp(quantile_function[idx_rem])
                )  # Equation 14

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

        if cumulative_prob == 0.0:  # or cumulative_prob == 1.0:
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
                        * (
                            p05_term ** (n / 2 - 1) / p1p_term
                            + (n / 2 - 1) * p05_term ** (n / 2 - 2) * ln_p_term
                        )
                    )

        density_function = density_functions[self.term]
        if not force_unbounded:
            if self.boundedness == "lower":  # Equation 13
                if 0 < cumulative_prob < 1:
                    density_function = density_function * np.exp(
                        -self.quantile(cumulative_prob, force_unbounded=True)
                    )
                elif cumulative_prob == 0:
                    density_function = 0
                else:
                    raise ValueError(
                        "Probability in call to density_m() cannot be equal to 1 with a lower-bounded distribution."
                    )

            elif self.boundedness == "upper":
                if 0 < cumulative_prob < 1:
                    density_function = density_function * np.exp(
                        self.quantile(cumulative_prob, force_unbounded=True)
                    )
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
                        density_function
                        * (1 + x_unbounded) ** 2
                        / ((self.ubound - self.lbound) * x_unbounded)
                    )
                if cumulative_prob == 0 or cumulative_prob == 1:
                    density_function = 0

        return density_function

    def get_cumulative_prob(self, x, lowerbound=0.0, upperbound=1.0):
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
        # todo: consider replacing brent's method with Newton's (or other), and provide the derivative of quantile, since it should be possible to obtain an analytic expression for that
        return optimize.brentq(f_to_zero, lowerbound, upperbound, xtol=1e-24, disp=True)

    def cdf(self, x):
        """
        This is where we override the SciPy method for the CDF.

        `x` may be a scalar or list-like.
        """
        if is_list_like(x):
            return [self.cdf(i) for i in x]
        if is_numeric(x):
            return self.get_cumulative_prob(x)

    def ppf(self, probability):
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
