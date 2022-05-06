import numpy as np
from math import gamma, e
from typing import Union

def upper_incomplete_gamma(a, x, iterations):
    """
    Implementation for upper incomplete gamma.
    """
    val = 1.0
    for d in reversed(range(1, iterations)):
        val = d * 2 - 1 - a + x + (d * (a - d)) / val
    return ((x ** a) * (e ** (-x))) / val


def chi2cdf(x, df, iterations=100):
    """
    Chi squared cdf function. This function can also be used from scipy,
    but to reduce the compilation size a seperate (slighty slower)
    implementation without scipy is written.
    """
    return 1 - upper_incomplete_gamma(0.5 * df, 0.5 * x, iterations) / gamma(0.5 * df)


class Experts:
    """
    Experts class. Contain the properties for all experts
    and decision makers. Also functions to add or remove
    experts are present in the class.
    """

    def __init__(self, project):
        """
        Constructor. Assigns all (empty) arrays and lists

        Parameters
        ----------
        project : anduryl.main.Project
            Project class
        """
        self.project = project
        self.M = {}
        self.ids = []
        self.names = []
        self.actual_experts = []
        self.decision_makers = []
        self.info_real = np.zeros((0))
        self.info_total = np.zeros((0))
        self.calibration = np.zeros((0))
        self.nseeds = np.zeros((0))
        self.comb_score = np.zeros((0))
        self.user_weights = np.zeros((0))
        self.info_per_var = np.zeros((0, 0))
        self.arraynames = ["user_weights", "info_real", "info_total", "calibration", "nseeds", "comb_score"]
        self.excluded = []
        # self.styles = []

    def get_exp(self, exptype="both"):
        """
        Returns a list of expert id's

        Parameters
        ----------
        exptype : str, optional
            Expert type, should be 'dm', 'actual' or 'both' (default)

        Returns
        -------
        list
            List of expert id's
        """
        if exptype == "both":
            return self.ids[:]
        elif exptype == "dm":
            return [self.ids[i] for i in self.decision_makers]
        elif exptype == "actual":
            return [self.ids[i] for i in self.actual_experts]
        else:
            raise TypeError(exptype)

    def get_idx(self, experts: Union[str, list, None]) -> Union[np.ndarray, int]:
        """
        Returns the idx of one or more experts in the list

        Parameters
        ----------
        experts : list, str of Nonetype
            List with experts, a single expert, 'dm' or 'actual' or None

        Returns
        -------
        np.ndarray or int
            Array with experts indices or a single expert index
        """
        if isinstance(experts, list):
            return np.array([self.ids.index(exp) for exp in experts])
        elif experts == "actual":
            return np.array(self.actual_experts)
        elif experts == "dm":
            return np.array(self.decision_makers)
        elif isinstance(experts, str):
            return self.ids.index(experts)
        elif experts is None:
            return np.ones(len(self.ids), dtype=bool)
        else:
            raise TypeError(f"Unexpected type {type(experts)}")

    def clear(self):
        """
        Clears all id's, names and counts.
        """
        # Empty lists
        del self.ids[:]
        del self.names[:]
        del self.actual_experts[:]
        del self.decision_makers[:]

        # Set arrays to nan
        for arr in self.arraynames:
            getattr(self, arr)[:] = np.nan
        # Empty dict
        self.M.clear()

    def initialize(self, nexperts, nitems):
        """
        Initialize (empty) class. Allocates the lists
        and arrays given the number of experts or items

        Parameters
        ----------
        nexperts : int
            Number of experts
        nitems : int
            Number of items
        """
        # Intialize lists
        self.ids.extend([[] * nexperts])
        self.names.extend([[] * nexperts])
        self.actual_experts.extend([[] * nexperts])

        # 1D arrays
        for arr in self.arraynames:
            arr = getattr(self, arr)
            arr.resize(nexperts, refcheck=False)
            arr[:] = np.nan

        # 2D arrays
        self.info_per_var.resize((nexperts, nitems), refcheck=False)

    def add_expert(self, exp_id, exp_name, assessment, exp_type, overwrite=False, full_cdf=None):
        """
        Add expert to project.

        Parameters
        ----------
        exp_id : str
            Expert ID
        exp_name : str
            Expert name
        assessment : numpy.ndarray
            Array with expert assessment values (Nquestions, Nquantiles+2)
        exp_type : str
            Type of expert. Can be 'actual' or 'dm'
        overwrite : bool, optional
            Whether to overwrite an existing expert ID, by default False
        full_cdf : np.ndarray
            Array with full expert CDF

        Raises
        ------
        KeyError
            If not overwrite and expert id already present
        TypeError
            If expert type is not one of 'actual' or 'dm'
        """
        if exp_id in self.ids and not overwrite:
            raise KeyError(f'Expert ID "{exp_id}" already present. Pick another or specify overwrite=True.')

        # Overwrite, so no need to resize
        elif (exp_id in self.ids) and overwrite:
            idx = self.get_idx(exp_id)
            self.project.assessments.array[idx, :, :] = assessment.T[None, 1:-1, :]

            # Add full cdf for decision maker
            if full_cdf is not None:
                self.project.assessments.full_cdf[exp_id] = full_cdf

            # Make sure the expert type is the same too

        # Else, append
        else:
            self.ids.append(exp_id)
            self.names.append(exp_name)
            # self.styles.append(style)

            # Resize expert arrays
            for name in self.arraynames:
                arr = getattr(self, name)
                arr.resize(arr.size + 1, refcheck=False)
                arr[-1] = np.nan

            shape = self.info_per_var.shape
            vals = self.info_per_var.copy()
            self.info_per_var.resize((shape[0] + 1, shape[1]), refcheck=False)
            self.info_per_var[:-1, :] = vals[:, :]

            # Resize assessments array
            shape = self.project.assessments.array.shape
            self.project.assessments.array.resize((shape[0] + 1, shape[1], shape[2]), refcheck=False)
            if assessment is not None:
                if len(self.project.assessments.quantiles) == assessment.shape[1]:
                    self.project.assessments.array[-1, :, :] = assessment.T[None, :, :]
                elif len(self.project.assessments.quantiles) == assessment.shape[1] - 2:
                    self.project.assessments.array[-1, :, :] = assessment.T[None, 1:-1, :]
                else:
                    raise ValueError()
            else:
                self.project.assessments.array[-1, :, :] = np.nan

            # Add index to list with actual experts or DMs
            if exp_type.lower() == "actual":
                self.actual_experts.append(len(self.ids) - 1)
            elif exp_type.lower() == "dm":
                self.decision_makers.append(len(self.ids) - 1)
            else:
                raise TypeError("Expert type not recognized.")

            # Add full cdf for decision maker
            if full_cdf is not None:
                self.project.assessments.full_cdf[exp_id] = full_cdf

    def remove_expert(self, exp_id):
        """
        Removes an experts from the class by id.
        Looks up the id in all the relevant lists and arrays,
        and removes the data from the element.

        Parameters
        ----------
        exp_id : str
            Expert id
        """

        # Check if present
        if exp_id not in self.ids:
            raise KeyError(f'Expert "{exp_id}" not in expert ids.')

        # Get index
        idx = self.ids.index(exp_id)
        # Remove from ids and names
        self.names.remove(self.names[idx])
        self.ids.remove(exp_id)

        # Remove index from list
        for lst in [self.actual_experts, self.decision_makers]:
            if idx in lst:
                lst.remove(idx)

        # Adjust other indexes of they where larger
        for lst in [self.actual_experts, self.decision_makers]:
            for i, item in enumerate(lst):
                if item > idx:
                    lst[i] -= 1

        # Remove from excluded
        if exp_id in self.excluded:
            self.excluded.remove(exp_id)

        # Remove bin counts
        if exp_id in self.M:
            del self.M[exp_id]

        # Remove from 1d arrays
        keep = np.ones(len(self.info_real), dtype=bool)
        keep[idx] = False
        keep = np.where(keep)[0]

        for name in self.arraynames:
            arr = getattr(self, name)
            vals = arr[keep]
            arr.resize(len(vals), refcheck=False)
            arr[:] = vals

        # 2D arrays
        vals = self.info_per_var[keep, :]
        self.info_per_var.resize(vals.shape, refcheck=False)
        self.info_per_var[:] = vals

        # Assessments
        vals = self.project.assessments.array[keep, :, :]
        self.project.assessments.array.resize(vals.shape, refcheck=False)
        self.project.assessments.array[:] = vals

    def count_realizations_per_bin(self, experts, items=None):
        """
        Devide the realizations in the quantile bins
        given by the experts

        Parameters
        ----------
        experts : list or None
            List of experts for which the realizations are counted
        items : array or None, optional
            Boolean array with the items to count. If None, all items are counted.
            This option can be used for excluding items when calculating
            robustness tables
        """
        # Check the used percentiles for calibration
        # The calibration score can (for now) only be calculated for a fixed number of percentiles
        idx = self.project.items.get_idx(question_type="seed")
        quants = self.project.items.use_quantiles[idx, :]
        pidx = quants.any(axis=0)
        if not np.array_equal(quants.all(axis=0), pidx):
            raise ValueError("Only a fixed number of percentiles can be used in the calibration questions")

        # Get values for all seed assessments, and replace NaN
        values = self.project.assessments.get_array("seed", experts)[:, pidx, :]
        if items is not None:
            values = values[:, :, items]

        # Get number of non nan answers per expert
        nonnan = (~np.isnan(values)).any(axis=1).sum(axis=-1)
        # Replace NaN values
        values[np.isnan(values)] = -np.inf

        # Get counts
        rls = self.project.items.realizations
        rls = rls[~np.isnan(rls)]

        # In case a selection of items is needed:
        if items is not None:
            rls = rls[items]

        # Determine which of the answers are smaller or equal to the realizations
        # Count contains the number of items for which the experts was lower than
        # one of the percentile bins. Taking the difference between these count
        # gives the number of realizations within one of the bins.
        count = np.sum(rls[None, None, :] <= values, axis=-1)
        Marr = np.empty((count.shape[0], count.shape[1] + 1), dtype=int)
        Marr[:, 0] = count[:, 0]
        Marr[:, 1:-1] = count[:, 1:] - count[:, :-1]
        Marr[:, -1] = nonnan - count[:, -1]
        dct = {}
        for exp, counts in zip(experts, Marr):
            dct[exp] = counts

        return dct

    def _information_score(self, experts, overshoot, bounds_for_experts=False, items=None):
        """
        Calculate the information score for the given experts

        Parameters
        ----------
        experts : list
            List with experts for which the information scores are calculated
        overshoot : float
            Overshoot (intrinsic range) for the bounds
        bounds_for_experts : bool, optional
            If true, the bounds are determined only for the given experts (instead of all experts).
            This option can be used for the robustness checks. By default False
        """

        # Get bounds for both seed and target questions
        if bounds_for_experts:
            lower, upper = self.project.assessments.get_bounds("both", overshoot=overshoot, experts=experts)
        else:
            lower, upper = self.project.assessments.get_bounds("both", overshoot=overshoot)

        # Get assessments
        values = self.project.assessments.get_array(experts=experts)
        nexperts, npercentiles, nitems = values.shape

        # Get the position of the expert
        expidxs = self.get_idx(experts)

        # Get index of answered per expert. Only if all percentiles are given, the info score is calculated
        valid = np.zeros((nexperts, nitems), dtype=bool)

        # Scale values to log
        scale = self.project.items.scales
        for iq in range(nitems):
            # Checker whether all the answers are filled in (a valid entry)
            use = self.project.items.use_quantiles[iq]
            valid[:, iq] = (~np.isnan(values[:, use, iq])).all(axis=1)
            # Scale to log
            if scale[iq] == "log":
                values[:, use, iq] = np.log(values[:, use, iq])

        for iq in range(len(self.project.items.ids)):
            use = self.project.items.use_quantiles[iq]
            percentiles = np.concatenate([[0.0], np.array(self.project.assessments.quantiles)[use], [1.0]])
            p = percentiles[1:] - percentiles[:-1]

            # Initialize bounds and fill limits
            bounds = np.zeros(len(percentiles))
            bounds[0] = lower[iq]
            bounds[-1] = upper[iq]

            for iexp, idx in enumerate(expidxs):
                if not valid[iexp, iq]:
                    self.info_per_var[iexp, iq] = 0.0
                    continue
                bounds[1:-1] = values[iexp, use, iq]
                # Calculate info per variable
                self.info_per_var[idx, iq] = np.log(upper[iq] - lower[iq]) + np.sum(
                    p * np.log(p / (bounds[1:] - bounds[:-1]))
                )

        # Calculate calibration score for seed (realizations) and total item set
        ridx = self.project.items.get_idx("seed")
        tidx = self.project.items.get_idx("both")

        # In case a selection of items is given:
        if items is not None:
            exclude = np.where(ridx)[0][~items]
            ridx[exclude] = False
            tidx[exclude] = False

        self.info_real[expidxs] = self.info_per_var[np.ix_(expidxs, ridx)].sum(axis=1) / (
            self.info_per_var[np.ix_(expidxs, ridx)] != 0.0
        ).sum(axis=1)
        self.info_total[expidxs] = self.info_per_var[np.ix_(expidxs, tidx)].sum(axis=1) / (
            self.info_per_var[np.ix_(expidxs, tidx)] != 0.0
        ).sum(axis=1)

        # print('Na berekenen:', self.info_per_var)

    def calibration_score(self, counts, Nmin, calpower):
        """
        Calculate calbration score

        Parameters
        ----------
        M : numpy.ndarray
            Number of realizations per question in each bin
        Nmin : int
            Minimum number of answered questions for All experts
        """

        # Get used percentiles
        idx = self.project.items.use_quantiles[self.project.items.get_idx("seed"), :].any(axis=0)
        quantiles = np.array(self.project.assessments.quantiles)[idx]

        # Get probabilities
        edges = np.concatenate([[0.0], quantiles, [1.0]])
        p = edges[1:] - edges[:-1]

        # Calculate calibration scores
        cal = np.zeros(len(counts))
        for i, (_, count) in enumerate(counts.items()):
            # Scale the number of realizations per bin
            s = count / count.sum()
            # Only use nonzero
            idx = s > 0.0
            # Calculate information score
            MI = np.sum(s[idx] * np.log(s[idx] / p[idx]))
            E = 2 * Nmin * MI * calpower
            # Test with chi squared
            cal[i] = 1 - chi2cdf(x=E, df=len(s) - 1)

        return cal


    def calculate_weights(self, overshoot, alpha, calpower, experts=None, items=None):
        """
        Calculate the weights of experts, based on the information score
        and the calibration score.

        Parameters
        ----------
        overshoot : float
            Overshoot or intrinsic range, used for determining the item bounds
        alpha : float
            Significance level for the calibration score. Experts with a lower
            calibration score get zero weight.
        calpower : float
            Calibration power, relative weight of the calibration compared
            to the information score
        experts : list, optional
            List with experts for which to calculate the weigths.
            By default None (all experts)
        items : array, optional
            Array with boolean index of items to take into account when
            calculating the weights. By default None (all items)
        """

        if experts is None:
            experts = self.ids

        # Get information score
        self._information_score(experts, overshoot, items=items)

        # Count the number of realizations per bin for the given
        # experts and item selection
        counts = self.count_realizations_per_bin(experts, items=items)
        self.M.update(counts)

        # Get minimum answered questions by actual experts
        Nmin = min(sum(self.M[self.ids[i]]) for i in self.actual_experts)

        # Get calibration score
        idx = self.get_idx(experts)
        self.calibration[idx] = self.calibration_score(counts, Nmin=Nmin, calpower=calpower)
        # Get number of answered items (used for GUI only)
        self.nseeds[idx] = np.array([vals.sum() for vals in counts.values()])
        # That's why the number of seed questions for DM's is set to NaN
        self.nseeds[self.decision_makers] = np.nan

        # Calculate weights based on realizations and calibration
        if alpha is not None:
            above_threshold = (self.calibration[idx] >= alpha).astype(int)
            self.comb_score[idx] = self.calibration[idx] * self.info_real[idx] * above_threshold
        else:
            self.comb_score[idx] = self.calibration[idx] * self.info_real[idx]

    def get_weights(self, weight_type, experts, alpha=None, exclude=None, calpower=None):
        """
        Get weights excluding given items. Specifically for robustness calculation.

        This method can excludes items from the weights, without actually removing
        these items from the project. By excluding an item the calibration scores
        change, so these are recalculated in the project.

        Parameters
        ----------
        weight_type : str
            Weight type, global, item, user or equal.
        experts : list
            Experts for which the weights are returned
        alpha : float, optional
            Significance level for the calibration score. If None, the weights
            are returnes for all possible significance levels (unique calibration scores)
        exclude : list, optional
            List with experts to exclude, can be used in robustness checks, by default None
        calpower : float, optional
            Calibration power, relative weight of the calibration compared
            to the information score. Can be None when no experts are exluded, and the4
            calibration score does not have to be recalculated.

        Returns
        -------
        tuple
            np.ndarray with weights per (alpha, expert, item) and np.ndarray with alphas
        """
        # Get index of experts for which the weights should be returned
        expidx = self.get_idx(experts)

        # In case of exlcuding items, get the calibration score
        if exclude is not None:

            # Count realization with exluding one or more items
            seed_idx = self.project.items.get_idx("seed", where=True)
            include = np.ones(len(seed_idx), dtype="bool")
            include[list(exclude)] = False
            actual_experts = [self.ids[i] for i in self.actual_experts]
            count_dct = self.count_realizations_per_bin(experts=actual_experts, items=include)

            # Recalculate calibration score for new counts
            Nmin = min(sum(count) for count in count_dct.values())
            cal = self.calibration_score(
                counts={exp: count_dct[exp] for exp in experts}, Nmin=Nmin, calpower=calpower
            )

        else:
            cal = self.calibration[expidx]

        # If alpha is not given, the alphas are retrieved from the calibration values
        if alpha is None:
            alphas = np.unique(cal)
        else:
            alphas = [alpha]

        # Initialize weights
        nquestions = len(self.project.items.ids)
        nexperts = len(experts)
        weights = np.zeros((len(alphas), nexperts, nquestions))

        if weight_type == "global":

            if exclude is None:
                # Get information score for all realizations if nothing to exclude
                info = self.info_real[expidx]
            else:
                # Or select only the included realizations
                ridx = seed_idx[include]
                # idx = np.ix_(expidx, ridx)
                info = self.info_per_var[expidx][:, ridx].sum(axis=1) / (
                    self.info_per_var[expidx][:, ridx] != 0.0
                ).sum(axis=1)

            # Fill with global weights, calculated for calibration questions
            for i, alpha in enumerate(alphas):
                above_threshold = cal >= alpha
                if above_threshold.any():
                    wperexp = info * cal * above_threshold.astype(int)
                    weights[i, :, :] = (wperexp / sum(wperexp))[:, None]

        # Return item weights, calculated for all (calibration and target) questions
        elif weight_type == "item":

            total_idx = np.ones(nquestions, dtype=bool)
            if exclude is not None:
                total_idx[list(exclude)] = False

            # Get information per variable and index
            info = self.info_per_var[expidx][:, total_idx]

            for i, alpha in enumerate(alphas):
                weights[i][:, total_idx] = info * (cal * (cal >= alpha).astype(int))[:, None]

            weights[:, :, total_idx] /= weights[:, :, total_idx].sum(axis=1)[:, None, :]

        # Return equal weights
        elif weight_type == "equal":
            # Assign equal weights
            nexp = weights.shape[1]
            weights[:, :, :] = (np.ones(nexp) / nexp)[None, :, None]

        # Return user weights
        elif weight_type == "user":
            # Check weights
            expert_user_weight, message = self.check_user_weights()
            if expert_user_weight is None:
                raise ValueError(message)
            # Assign user weights
            weights[:, :, :] = expert_user_weight[None, :, None]

        else:
            raise NotImplementedError(weight_type)

        return weights, alphas

    def check_user_weights(self):
        """
        Checks the assigned user weights and returns on
        info or warning message.

        Returns
        -------
        Weights and message
            User weights which are None if invalid, and a message.
        """

        # Check weights
        expert_user_weight = self.user_weights[self.actual_experts]
        if np.isnan(expert_user_weight).all():
            return None, f"Assign user weights before calculating a decision maker with this option."

        # Check if less than 0.0
        if (expert_user_weight < 0.0).any():
            return None, f"All user weights should be equal to or greater than 0.0."

        # Set nan values to 0.0
        expert_user_weight[np.isnan(expert_user_weight)] = 0.0
        if (expert_user_weight == 0.0).all():
            return None, f"All assigned user weights are 0.0. At least one weight should be greater than 0.0."

        # Check if sum == 0.0
        if expert_user_weight.sum() != 1.0:
            weights = expert_user_weight / expert_user_weight.sum()
            return (
                weights,
                f"Sum of user weights is not equal to 1.0 (current sum is {expert_user_weight.sum()}). Weights are normalised.",
            )

        return expert_user_weight, ""

    def as_dict(self, orient="columns"):
        """
        Returns the information scores for all variables,
        the realizations and the calibration scores for
        all experts as a Python dictionary. The result
        can easily be converted to a pandas DataFrame with
        pandas.DataFrame.from_dict([results])

        Parameters
        ----------
        orient : str, optional
            First dimensions in dictionary. If columns, the results
            variables are the first dimension. If index, the experts.
            By default 'columns', similar to the pandas default.

        Returns
        -------
        dictionary
            Dictionary with information and calibration scores
        """

        lists = (
            self.ids,
            self.names,
            self.info_total,
            self.info_real,
            self.calibration,
            self.nseeds,
            self.comb_score,
            self.user_weights,
        )

        if orient not in ["columns", "index"]:
            raise KeyError(f"Orient {orient} should be 'columns' or 'index'.")

        dct = {}
        for exp_id, name, infotot, inforeal, cal, nseed, weight, user_weight in zip(*lists):
            dct[exp_id] = {
                "Name": name,
                "Info. score total": infotot,
                "Info. score real.": inforeal,
                "Calibration score": cal,
                "Answered seed items": nseed,
                "Weight": weight,
                "User weight": user_weight,
            }

        if orient == "columns":
            # Transpose
            keys = dct[exp_id].keys()
            dct = {key: {k: dct[k][key] for k in dct if key in dct[k]} for key in keys}

        return dct

    def to_latex(self):
        lines = [
            r"\begin{tabularx}{\linewidth}{XXXXX}",
            r"\toprule",
            r"{}                      & Calibration score            & \multicolumn{2}{c}{Information score} & Weight               \\",
            r"\cmidrule(lr){3-4}",
            r"{} &                      & All   & Calibr.                 &                      \\ \midrule",
        ]

        lists = (
            self.ids,
            self.info_total,
            self.info_real,
            self.calibration,
            self.comb_score,
        )

        for i, (exp_id, infotot, inforeal, cal, weight) in enumerate(zip(*lists)):
            if i == self.decision_makers[0]:
                lines[-1] = rf"{lines[-1]} \midrule"
            lines.append(rf"{exp_id} & {cal:.3f} & {infotot:.3f} & {inforeal:.3f} & {weight:.3f} \\")

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabularx}")

        return "\n".join(lines)
