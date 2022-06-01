import types
from copy import deepcopy

import numpy as np
from anduryl.core import calculate
from anduryl.core.assessments import Assessments
from anduryl.core.experts import Experts
from anduryl.core.items import Items
from anduryl.io.project import ProjectIO
from anduryl.ui.dialogs import NotificationDialog
from anduryl.io.settings import WeightType

class Project:
    """
    Main project class. Contains experts, items, assessments
    and results.
    """

    def __init__(self):
        """
        Constructor.

        Note that a project has two types of results. The main results 
        and the results per decision maker.
        The second one are added when anduryl is used from the GUI.
        """
        
        # Link IO class
        self.io = ProjectIO(self)
        
        # Add experts, assessments and items
        self.experts = Experts(self)
        self.assessments = Assessments(self)
        self.items = Items(self)

        # Add main results
        self.main_results = Results(
            settings=None,
            experts=self.experts,
            assessments=self.assessments,
            items=self.items
        )

        # Add derived results
        self.results = {}

    def __repr__(self):
        methods = []
        properties = []
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            elif isinstance(getattr(self, attr), types.MethodType):
                methods.append(attr)
            else:
                properties.append(attr)
        methods = '\n - '.join(methods)
        properties = '\n - '.join(properties)
        
        return f'Main project class.\nProperties:\n - {properties}\nMethods:\n - {methods}'

    def __deepcopy__(self, memo):
        """
        Create a deepcopy without the results, since this would lead
        to recursive copying.
        """
        copy = type(self)()
        memo[id(self)] = copy
        copy.experts = deepcopy(self.experts, memo)
        copy.items = deepcopy(self.items, memo)
        copy.assessments = deepcopy(self.assessments, memo)
        return copy
        

    def initialize(self, nexperts, nseed, ntarget, nquantiles):
        """
        Initialize the project by initializing all the arrays and lists.
        
        Parameters
        ----------
        nexperts : int
            Number of experts
        nseed : int
            Number of seed questions
        ntarget : int
            Number of target questions
        nquantiles : int
            Number of quantiles
        """

        self.experts.clear()
        self.experts.initialize(nexperts, nseed + ntarget)

        self.items.clear()
        self.items.initialize(nseed + ntarget, nquantiles)

        self.assessments.clear()
        self.assessments.initialize(nexperts, nseed + ntarget, nquantiles)

    def to_results(self, settings):
        """
        Copy the project to a results class, which can be used to calculate
        the decision maker of robustness. Add the results to the result dict.
                
        Parameters
        ----------
        settings : dictionary
            Dictionary with the calculation settings.
        """
        # Copy the project
        projectcopy = deepcopy(self)
        copied_settings = deepcopy(settings)
        self.results[copied_settings.id] = Results(
            settings=copied_settings,
            experts=projectcopy.experts,
            assessments=projectcopy.assessments,
            items=projectcopy.items,
        )

    def calculate_decision_maker(self, dm_settings, overwrite=False):
        """
        Convenience function for calculating the DM for the main results.
        For parameters see the method calculate_decision_maker in the Result class.
        """
        self.main_results.calculate_decision_maker(
            dm_settings=dm_settings,
            overwrite=overwrite
        )

    def calculate_item_robustness(self, weight_type, overshoot, max_exclude, min_exclude=0, calpower=1.0, alpha=None):
        """
        Convenience function for calculating the item robustness for the main results.
        For parameters see the method calculate_item_robustness in the Result class.
        """
        self.main_results.calculate_item_robustness(
            min_exclude=min_exclude,
            max_exclude=max_exclude,
            weight_type=weight_type,
            overshoot=overshoot,
            calpower=calpower,
            alpha=alpha
        )

    def calculate_expert_robustness(self, weight_type, overshoot, max_exclude, min_exclude=0, calpower=1.0, alpha=None):
        """
        Convenience function for calculating the expert robustness for the main results.
        For parameters see the method calculate_expert_robustness in the Result class.
        """
        self.main_results.calculate_expert_robustness(
            min_exclude=min_exclude,
            max_exclude=max_exclude,
            weight_type=weight_type,
            overshoot=overshoot,
            calpower=calpower,
            alpha=alpha
        )

    def add_results_from_settings(self, calc_settings):
        """
        Method to add the results from settings. The settings contain
        all the information to (re-)calculate the results.
        
        Parameters
        ----------
        calc_settings : dict
            Dictionary with calculation settings
        """

        # Freeze the results
        self.to_results(calc_settings)
        # Get the results that are just copied (frozen)
        results = self.results[calc_settings.id]

        # Only actual experts needed in results, remove other decision makers
        exps = self.experts.get_exp('actual')
        exp_ids = results.experts.ids[:]
        for exp in exp_ids:
            if exp not in exps:
                results.experts.remove_expert(exp)

        # Exclude experts that have no answered (seed) questions
        actual_experts = results.experts.get_exp('actual')
        
        if calc_settings.weight in [WeightType.GLOBAL, WeightType.ITEM]:
            answers = results.assessments.get_array(question_type='seed', experts=actual_experts)
        else:
            answers = results.assessments.get_array(question_type='both', experts=actual_experts)

        # NaN-waarden: minstens één van de percentielen voor alle vragen
        # NaN-waarden: elk van de percentielen voor alle vragen
        nanexperts = np.isnan(answers).all(-1).all(-1)
        nanexperts = np.array(actual_experts)[nanexperts].tolist()
        if any(nanexperts):
            exps = ', '.join(nanexperts)
            results.experts.excluded.extend(nanexperts)
            if len(nanexperts) == 1:
                NotificationDialog(f'Expert {exps} has not answered any (seed) questions, and is excluded from the calculation.')
            else:
                NotificationDialog(f'Experts {exps} have not answered any questions, and are excluded from the calculation.')

        # Exclude experts and items that are unchecked
        for exp in results.experts.excluded:
            if exp in results.experts.ids:
                results.experts.remove_expert(exp)
        for item in results.items.excluded:
            results.items.remove_item(item)

        # Check if there are any experts and items left
        if len(results.experts.actual_experts) == 0:
            NotificationDialog('All experts are excluded from the calculation. Add at least one expert before calculating a decision maker.')
            return False

        if len(results.items.ids) == 0:
            NotificationDialog('All items are excluded from the calculation. Add at least one item before calculating a decision maker.')
            return False

        # Get alpha, dependend on optimisation settings
        if (calc_settings.weight in [WeightType.GLOBAL, WeightType.ITEM] and not calc_settings.optimisation):
            # In case of no optimisation and global and item, use the user defined variable
            pass
        elif calc_settings.weight in [WeightType.USER, WeightType.EQUAL]:
            # In case of user or equal weight, do not use a threshold, since it is user defined or
            # would potentially disqualify all experts
            calc_settings.alpha = 0.0
        else:
            # In case of global or item and optimisation, set alpha to None (meaning it will be optimised)
            calc_settings.alpha = None

        # Calculate DM, and return the used alpha
        results.calculate_decision_maker(
            dm_settings=calc_settings,
            main_results=self.main_results
        )        

        # Calculate robustness tables for excluding a single item
        if calc_settings.robustness and results.items.get_idx('seed').sum() > 1:
            results.calculate_item_robustness(
                max_exclude=1,
                weight_type=calc_settings.weight,
                overshoot=calc_settings.overshoot,
                alpha=calc_settings.alpha,
                calpower=calc_settings.calpower,
            )

        if calc_settings.robustness and len(results.experts.actual_experts) > 1:
            results.calculate_expert_robustness(
                max_exclude=1,
                weight_type=calc_settings.weight,
                overshoot=calc_settings.overshoot,
                alpha=calc_settings.alpha,
                calpower=calc_settings.calpower,
            )

        results.experts.weights = results.get_weight_in_dm()

        return True

class Results:
    """
    Result class. Contains a copy (when using GUI) of the experts, items and assessments
    from the moment the results were calculated. The result class
    contains methods to calculate decision makers and robustenss. These
    results are calculated from the copy of the experts, items and
    assessments, and will therefor not change when those are changed in the GUI.
    """

    def __init__(self, settings, experts, assessments, items):
        """
        Constructor
        
        Parameters
        ----------
        settings : dict
            Dictionary with calculating settings
        experts : expert class
            Expert class with the experts information and methods
        assessments : assessment class
            Assessment class with the assessments information and methods
        items : item class
            Item class with the items information and methods
        """
        self.settings = settings
        self.experts = experts
        self.assessments = assessments
        self.items = items
        self.alpha_opt = None

        # Dictionary for saving the robustness results
        self.item_robustness = {}
        self.expert_robustness = {}

    def get_weight_in_dm(self):

        if self.settings is None:
            return np.full(len(self.experts.ids), np.nan)
        
        # Get weights
        if self.settings.weight in [WeightType.GLOBAL, WeightType.ITEM]:
            weights = self.experts.comb_score.copy()

        elif self.settings.weight == WeightType.EQUAL:
            n = len(self.experts.actual_experts)
            weights = np.ones_like(self.experts.comb_score) / n

        elif self.settings.weight == WeightType.USER:
            weights = np.zeros_like(self.experts.comb_score)
            idx = ~np.isnan(self.experts.user_weights)
            idx[self.experts.get_idx("dm")] = False
            weights[idx] += self.experts.user_weights[idx] / self.experts.user_weights[idx].sum()

        # Correct for alpha threshold
        if self.alpha_opt is not None:
            weights[self.experts.calibration < self.alpha_opt] = 0.0

        # Set DM to zero
        dm_idx = self.experts.get_idx("dm")
        weights[dm_idx] = np.nan

        isnan = np.isnan(weights)
        if not isnan.all():
            np.divide(weights, np.nansum(weights), out=weights, where=~isnan)

        return weights

    def calculate_decision_maker(self, dm_settings, overwrite=False, main_results=None):
        """
        Method to calculate the decision maker, given some settings from the parameters.
        
        Parameters
        ----------
        weight_type : str
            Weigth type: global, item, equal or user
        overshoot : float
            Intrinsic range, gives the total range per item
        exp_id : str
            ID by which expert is added to results
        calpower : float, optional
            Calibration power, a factor to weigh the calibration to the information score
        exp_name : str, optional
            Name by which expert is added to results, by default None
        alpha : float or Nonetype, optional
            Significance level, the minimum calibration value to take expert into account
        main_results : result class, optional
            Main Results class to which to results are added, by default None
        """

        # Calculate decision maker
        DM, F_DM, self.alpha_opt = calculate.decision_maker(
            experts=self.experts,
            items=self.items,
            assessments=self.assessments,
            dm_settings=dm_settings
        )       

        # Add to experts and calculate weight for DM
        exp_name = dm_settings.id if dm_settings.name is None else dm_settings.name
        self.experts.add_expert(exp_id=dm_settings.id, exp_name=exp_name, assessment=DM, exp_type='dm', overwrite=overwrite, full_cdf=F_DM)

        final_settings = dm_settings.copy()
        final_settings.alpha = self.alpha_opt
        self.experts.calculate_weights(dm_settings=dm_settings, experts=[dm_settings.id])

        # Add to main results. When using only the code (without GUI) this is not necessary.
        if main_results is not None:

            # In case of excluded items, correct shape
            if any(self.items.excluded):
                DM_full = np.full((len(main_results.items.ids), len(main_results.assessments.quantiles)+2), np.nan)
                item_idx = [item in self.items.ids for item in main_results.items.ids]
                DM_full[item_idx, :] = DM
            else:
                DM_full = DM

            # Add expert to the results
            main_results.experts.add_expert(
                exp_id=dm_settings.id, exp_name=exp_name, assessment=DM_full, exp_type='dm', overwrite=False, full_cdf=F_DM)
            
            # Copy weights etc. from the calculated results to the main results, so that
            # they are viewed in the expert table in the GUI
            main_idx = main_results.experts.get_idx(self.experts.ids)
            for name in main_results.experts.arraynames:
                arr = getattr(main_results.experts, name)
                arr[main_idx] = getattr(self.experts, name)

    def calculate_item_robustness(self, weight_type, overshoot, max_exclude, min_exclude=0, calpower=1.0, alpha=None, progress_func=None):
        """
        Calculate calibration and information scores by excluding items.
        This gives a measure for the robustness of the results
        
        Parameters
        ----------
        weight_type : str
            Weigth type: global, item, equal or user
        overshoot : float
            Intrinsic range, gives the total range per item
        max_exclude : int
            Maximum number of items to exclude
        min_exclude : int, optional
            Minumum number of items to exclude, by default 0
        calpower : float, optional
            Calibration power, a factor to weigh the calibration to the information score, by default 1.0
        alpha : float or Nonetype, optional
            Significance level, the minimum calibration value to take expert into account
        progress_func : function, optional
            Function to which the progress can be passed, for the GUI, by default None
        """
        # Calculate robustness for excluding a number of items, and pass directly to
        # result dictionary
        self.item_robustness.update(calculate.item_robustness(
            experts=self.experts,
            items=self.items,
            assessments=self.assessments,
            min_exclude=min_exclude,
            max_exclude=max_exclude,
            weight_type=weight_type,
            alpha=alpha,
            overshoot=overshoot,
            calpower=calpower,
            progress_func=progress_func
        ))

    def calculate_expert_robustness(self, weight_type, overshoot, max_exclude, min_exclude=0, calpower=1.0, alpha=None, progress_func=None):
        """
        Calculate calibration and information scores by excluding experts.
        This gives a measure for the robustness of the results
        
        Parameters
        ----------
        weight_type : str
            Weigth type: global, item, equal or user
        overshoot : float
            Intrinsic range, gives the total range per item
        max_exclude : int
            Maximum number of items to exclude
        min_exclude : int, optional
            Minumum number of items to exclude, by default 0
        calpower : float, optional
            Calibration power, a factor to weigh the calibration to the information score, by default 1.0
        alpha : float or Nonetype, optional
            Significance level, the minimum calibration value to take expert into account
        progress_func : function, optional
            Function to which the progress can be passed, for the GUI, by default None
        """
        # Calculate robustness for excluding a number of experts, and pass directly to
        # result dictionary
        self.expert_robustness.update(calculate.expert_robustness(
            experts=self.experts,
            items=self.items,
            assessments=self.assessments,
            min_exclude=min_exclude,
            max_exclude=max_exclude,
            weight_type=weight_type,
            alpha=alpha,
            overshoot=overshoot,
            calpower=calpower,
            progress_func=progress_func
        ))

    def get_plot_data(self, experts=None, items=None, plottype='cdf', full_dm_cdf=True):
        """
        Get data in overview, convenient for plotting.

        Parameters
        ----------
        experts : [type]
            [description]
        plottype : str, optional
            [description], by default 'cdf'
        full_dm_cdf : bool, optional
            [description], by default True
        """

        if plottype not in ['cdf', 'pdf', 'range', 'exc prob']:
            raise KeyError(f'Plottype: {plottype} not understood.')

        # Get expert assessments and bounds for question
        assessments = {}

        if experts is None:
            experts = self.experts.ids[:]
        # elif experts
        if items is None:
            items = self.items.ids[:]

        # For each item
        for item in items:
            # Get the item position in the items list
            iitem = self.items.ids.index(item)
            # self.get_bounds(experts=experts, overshoot)
            # lower = self.lower_k[iitem]
            # upper = self.upper_k[iitem]

            # For each expert 
            for expert in experts:
                # Get position of expert in the lists
                iexp = self.experts.ids.index(expert)
                # Check if expert is a decision maker, and if the full cdf's are expected
                if iexp in self.experts.decision_makers and full_dm_cdf:
                    # If so, add the full experts cdf 
                    assessments[(item, expert)] = {
                        'quantile': self.assessments.full_cdf[expert][iitem][:, 1],
                        'value': self.assessments.full_cdf[expert][iitem][:, 0]
                    }
                else:
                    # Else, just add the percentiles, including the lower and upper bound
                    values = self.assessments.array[iexp, :, iitem]
                    idx = ~np.isnan(values)
                    assessments[(item, expert)] = {
                        'quantile': np.array(self.assessments.quantiles)[idx],
                        'value': values[idx]
                    }
        
        # # Convert bounds form log scale to uniform scale in case of log background
        # if self.results.items.scales[itemid] == 'log':
        #     lower = np.exp(lower)
        #     upper = np.exp(upper)

        return assessments
        