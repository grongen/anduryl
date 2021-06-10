from itertools import combinations

import numpy as np
from numpy.core.multiarray import interp as compiled_interp


def decision_maker(experts, items, assessments, weight_type, overshoot, alpha, calpower):
    """
    Calculate decision maker (DM).

    This function can be applied with and without optimisation, and for different weight types.

    Pseudo code
    -----------
    Calculate calibration and information score for each expert
    Get answers of all experts, and scale to log when it is a log-scale question
    Get weights for all experts, given the chosen weight type.
    Get lower and upper bound for each item
    Get the CDF for all experts and items, as well as the unique answers.
    for each item:
        Multiply the CDF per expert with the weight of the expert, and sum for all experts (dot product)
        for each significance level (only one if no optimistion):
            Interpolate the percentiles within the weighted answers
            Convert the log-scale questions back to a linear scale
    if optimisation:
        Create an expert (DM) for each significance level, and pick the one with the highest weight.
    else:
        Create an expert (DM) for the given significance level
        
    Parameters
    ----------
    experts : anduryl.core.experts.Experts
        Expert class with the experts information and methods
    items : anduryl.core.items.Items
        Item class with the items information and methods
    assessments : anduryl.core.assessments.Assessments
        Assessment class with the assessments information and methods
    weight_type : str
        Weigth type: global, item, equal or user
    overshoot : float
        Intrinsic range, gives the total range per item
    alpha : float
        Significance level, the minimum calibration value to take expert into account
    calpower : float
        Calibration power, a factor to weigh the calibration to the information score
    """
    
    # Calculate weights for all actual experts
    experts.calculate_weights(
        overshoot=overshoot,
        alpha=alpha,
        calpower=calpower,
        experts=experts.get_exp('actual')
    )

    # Check if given alpha is not too high
    if alpha is not None:
        if alpha > experts.calibration[experts.actual_experts].max():
            raise ValueError('Given significance level (alpha) is higher than maximum calibration score, so all experts are excluded. Choose a lower significance level.')

    # Get the values for the items
    values = assessments.get_array(question_type='both', experts='actual')
    nexperts, npercentiles, nitems = values.shape
    
    # Scale values to log, if the background scale is log
    scale = items.scale
    for iq in range(nitems):
        if scale[iq] == 'log':
            use = items.use_quantiles[iq]
            values[:, use, iq] = np.log(values[:, use, iq])

    # Get weights
    actual_experts = experts.get_exp('actual')
    
    # Get weights. Returns an array of size Nalpha, Nexperts, Nquestions
    weights, alphas = experts.get_weights(weight_type=weight_type, experts=actual_experts, alpha=alpha)
    
    # Get bounds for both seed and target questions
    qlower, qupper = assessments.get_bounds('both', overshoot=overshoot)
    
    # Get the expert CDF's and distinct answers
    F_ex, all_answers = get_expert_CDFs(np.array(assessments.quantiles), items.use_quantiles, values, qlower, qupper)

    # Collect CDF
    DM = np.full((len(alphas), nitems, npercentiles + 2), np.nan)
    F_DM = {}

    # Get DM for each item
    for iq in range(nitems):

        # Determine what experts have not answered the question
        use = np.where(items.use_quantiles[iq])[0]
        item_quants = np.array(assessments.quantiles)[use]
        no_answer = np.isnan(values[:, use, iq]).any(axis=1)
        use += 1

        # Re-normalize weights without experts that have not answered
        if no_answer.any():
            weights[:, no_answer, iq] = 0.0
            numerator = weights[:, :, iq].sum(axis=1)[:, None]
            weights[:, :, iq] /= numerator

        # Weight the experts, by getting the weighted sum (in product) of the quantiles
        F_DM[iq] = np.dot(F_ex[iq], weights[:, :, iq].T)
        
        # For each alpha (weight threshold), get the DM by interpolating the project quantiles
        # in the weighted CDF and all answers
        for ialpha in range(len(alphas)):
            # Determine decision makers for all alphas
            DM[ialpha, iq, 0] = qlower[iq]
            DM[ialpha, iq, -1] = qupper[iq]
            DM[ialpha, iq, use] = compiled_interp(item_quants, F_DM[iq][:, ialpha], all_answers[iq])
            
            # If background scale is logaritmic, the values have to be converted back to their
            # original scale, so take the exponent.
            if scale[iq] == 'log':
                DM[ialpha, iq, use] = np.exp(DM[ialpha, iq, use])

    # In case of optimisation, find the optimal alpha
    if alpha is None:
        # Now the DM is known for each question and weight threshold, find the optimal threshols
        # Get weight for each decision maker
        exps = [f'tmp{i}' for i in range(len(alphas))]
        for (tmp_id, DMassessment) in zip(exps, DM):
            # Calculate weight of DM
            experts.add_expert(exp_id=tmp_id, exp_name=tmp_id, assessment=DMassessment, exp_type='dm', overwrite=True)
        # Calculate weights for all temporary experts
        experts.calculate_weights(overshoot=overshoot, experts=exps, alpha=alphas, calpower=calpower)
        # Get the alpha for the highest weight
        imax = np.argmax(experts.weights[experts.get_idx(exps)])
        # Remove all experts
        for exp in exps:
            experts.remove_expert(exp)
            
    # Else there is only one DM, use this one.
    else:
        imax = 0
        # Else only use the given weight
        alphas = [alpha]

    # Get full expert CDF
    for iq in range(nitems):
        if scale[iq] == 'log':
            F_DM[iq] = np.c_[np.exp(all_answers[iq]), F_DM[iq][:, imax]]
        else:
            F_DM[iq] = np.c_[all_answers[iq], F_DM[iq][:, imax]]

    return DM[imax], F_DM, alphas[imax]

def get_expert_CDFs(quantiles, use_quantiles, values, qlower, qupper):
    """
    Method to get the uniform CDF's of the expert assessments, based
    on their answers and the lower and upper bounds (with overshoot).

    This method is defined seperately since it only has to be called once
    while calculating for example the robustness per item. The method
    returns the CDF (Nanswers, Nexperts) per item, as well as the unique
    answers per item.
    
    Parameters
    ----------
    values : numpy.ndarray
        Three dimensional array with assessments (Nexpert, Npercentile, Nitem)
    qlower : numpy.ndarray
        One dimensional array with lower bound per item, overshoot is included
    qupper : numpy.ndarray
        One dimensional array with upper bound per item, overshoot is included
    """

    nexperts, _, nitems = values.shape
    
    F_ex, all_answers = {}, {}

    for iq in range(nitems):

        # Combine quantiles with lower and upper limit
        full_quantiles = np.concatenate([[0.0], quantiles[use_quantiles[iq]], [1.0]])
        
        # Collect all experts and quantiles for the question
        answers = values[:, use_quantiles[iq], iq]
        all_answers[iq] = np.concatenate([[qlower[iq]], np.unique(answers[~np.isnan(answers)]), [qupper[iq]]])
        
        # Initialize
        F_ex[iq] = np.zeros((len(all_answers[iq]), nexperts))
        expert_answers = np.zeros(use_quantiles[iq].sum() + 2)
    
        # Get expert answers, and interpolate all answers in the expert answers and the 
        # quantiles, to get the quantiles for every answer
        expert_answers[0] = qlower[iq]
        expert_answers[-1] = qupper[iq]

        # Determine what experts have not answered the question
        no_answer = np.isnan(answers).any(axis=1)
            
        for iex in range(nexperts):
            # Skip if not answered
            if no_answer[iex]:
                continue

            # Add to DM CDF. Note that the answers have already been converted to the background measure
            expert_answers[1:-1] = answers[iex]
            F_ex[iq][:, iex] = compiled_interp(all_answers[iq], expert_answers, full_quantiles)

    return F_ex, all_answers

def get_combinations(items, min_exclude, max_exclude, always_exclude=None):
    """
    Get combinations of excluded items.
    
    Parameters
    ----------
    items : list
        List of items for from which n_items are excluded
    min_exclude : int
        Minimum number of excluded items, combinations are generated
        with at least min_exclude excluded items
    max_exclude : int
        Maximum number of excluded items, combinations are generated
        with at least max_exclude excluded items
    always_exclude : list, optional
        List with items to exclude from all combinations, by default None
    
    Returns
    -------
    list
        List with combinations of included items
    """

    if max_exclude >= len(items):
        raise ValueError(f'Max number of excluded items ({max_exclude}) can not be equal or greater than the total number of items ({len(items)}).')
    
    if always_exclude is None:
        always_exclude = []

    # Check always exclude presence
    for item in always_exclude:
        if item not in items:
            raise KeyError(f'{item} is not in the given item list, so can not be excluded.')

    # Create index lists, remove always exclude items
    total_index = list(range(len(items)))
    for item in reversed(items):
        if item in always_exclude:
            total_index.remove(items.index(item))
    
    # Get combinations of excluded items
    combs = []
    for n in range(min_exclude, max_exclude+1):
        combs.extend(list(combinations(total_index, n)))

    return combs


def item_robustness(min_exclude, max_exclude, experts, items, assessments, weight_type, overshoot, alpha=None, calpower=1.0, progress_func=None):
    """
    Calculate calibration and information scores by excluding items.
    
    This function is generally similar to calculating a single decision maker
    for each combination of excluded items.
    
    The expert CDF's and answers are calculated only once, since these are
    equal for all combinations.
    
    Parameters
    ----------
    min_exclude : int, optional
        Minimum number of items to exclude
    max_exclude : int
        Maximum number of items to exclude
    experts : anduryl.core.experts.Experts
        Expert class with the experts information and methods
    assessments : anduryl.core.assessments.Assessments
        Assessment class with the assessments information and methods
    items : anduryl.core.items.Items
        Item class with the items information and methods
    weight_type : str
        Weigth type: global, item, equal or user
    overshoot : float
        Intrinsic range, gives the total range per item
    alpha : float or Nonetype, optional
        Significance level, the minimum calibration value to take expert into account
    calpower : float, optional
        Calibration power, a factor to weigh the calibration to the information score, by default 1.0
    progress_func : function, optional
        Function to which the progress can be passed, for the GUI, by default None
    """
    if weight_type not in ['global', 'item']:
        raise KeyError('Robustness table can only be calculated for item of global weight.')

    # Calculate information score per item and expert on beforehand
    actual_experts = experts.get_exp('actual')
    experts._information_score(actual_experts, overshoot)
    # Calculate counts, since Nmin is required later in the calculation
    experts.M.update(experts.count_realizations_per_bin(actual_experts))
    
    # Get the values for the items
    values = assessments.get_array(question_type='both', experts='actual')
    nexperts, npercentiles, nitems = values.shape
    seed_idx = items.get_idx('seed')
    seed_ids = [item for i, item in enumerate(items.ids) if seed_idx[i]]
    
    # Get combinations of items to exclude
    combs = get_combinations(items=seed_ids, min_exclude=min_exclude, max_exclude=max_exclude)
    
    # Scale values to log, if the background scale is log
    scale = items.scale
    for iq in range(nitems):
        if scale[iq] == 'log':
            use = items.use_quantiles[iq]
            values[:, use, iq] = np.log(values[:, use, iq])

    # Get bounds for both seed and target questions
    qlower, qupper = assessments.get_bounds('both', overshoot=overshoot)
    
    # Get the expert CDF's and distinct answers
    F_ex, all_answers = get_expert_CDFs(np.array(assessments.quantiles), items.use_quantiles, values, qlower, qupper)

    results = {}
    totexps = set()
    
    # Loop trough all combinations of excluded itemss
    for comb in combs:

        if progress_func is not None:
            progress_func()
        
        # Get the weights and thresholds for exluding some of the items
        weights, alphas = experts.get_weights(
            experts=actual_experts, weight_type=weight_type, alpha=alpha, exclude=comb, calpower=calpower)

        # Collect CDF
        DM = np.full((len(alphas), nitems, npercentiles + 2), np.nan)

        # If all weights are zero, it is not possible to calculate the DM
        if (weights == 0.0).all():
            results[tuple(seed_ids[i] for i in comb)] = (np.nan, np.nan, np.nan)
            continue


        # Get DM for each item
        for iq in range(nitems):
            
            # Get quantiles and index for item
            use = np.where(items.use_quantiles[iq])[0]
            item_quants = np.array(assessments.quantiles)[use]
            
            if iq in comb:
                DM[:, iq, :] = np.nan
                continue
                
            # Determine what experts have not answered the question
            no_answer = np.isnan(values[:, use, iq]).any(axis=1)
            use += 1
                        
            # Re-normalize weights without experts that have not answered
            if no_answer.any():
                weights[:, no_answer, iq] = 0.0
                weights[:, :, iq] /= weights[:, :, iq].sum(axis=1)[:, None]
            
            
            # Weight the experts, by getting the weighted sum (in product) of the quantiles
            F_DM = np.dot(F_ex[iq], weights[:, :, iq].T)

            # For each alpha (weight threshold), get the DM by interpolating the project quantiles
            # in the weighted CDF and all answers
            for ialpha in range(len(alphas)):
                # Determine decision makers for all alphas
                DM[ialpha, iq, 0] = qlower[iq]
                DM[ialpha, iq, -1] = qupper[iq]
                DM[ialpha, iq, use] = compiled_interp(item_quants, F_DM[:, ialpha], all_answers[iq])
                
                # If background scale is logaritmic, the values have to be converted back to their
                # original scale, so take the exponent.
                if scale[iq] == 'log':
                    DM[ialpha, iq, use] = np.exp(DM[ialpha, iq, use])

        # Create a boolean array with the items (seed questions) to include
        itembool = np.asarray([(iq not in comb) for iq in range(len(seed_ids))])

        # oldM = experts.M.copy()
        
        # In case of optimisation, find the optimal alpha
        if alpha is None:
            # Now the DM is known for each question and weight threshold, find the optimal threshols
            # Get weight for each decision maker
            exps = [f'tmp{i}' for i in range(len(alphas))]
            totexps = totexps.union(set(exps))
            for (tmp_id, DMassessment) in zip(exps, DM):
                # Calculate weight of DM
                experts.add_expert(exp_id=tmp_id, exp_name=tmp_id, assessment=DMassessment, exp_type='dm', overwrite=True)
            
            # Update actual expert item count
            experts.M.update(experts.count_realizations_per_bin(experts.get_exp('actual'), items=itembool))
                    
            # Calculate weights
            experts.calculate_weights(overshoot=overshoot, experts=exps, alpha=alphas, calpower=calpower, items=itembool)
            # Get the alpha for the highest weight
            imax = np.argmax(experts.weights[experts.get_idx(exps)])
            
        # Else there is only one DM, use this one.
        else:
            exps = ['tmp0']
            imax = 0
            totexps = exps
            # Add final expert and calculate weight
            # Add expert as decision maker, so that the (reduced) number of valid answers is used in calculating the calibration score
            experts.add_expert(exp_id='tmp0', exp_name='tmp0', assessment=DM[imax], exp_type='dm', overwrite=True)
            # Calculate Nmin including DM
            # Update actual expert item count
            experts.M.update(experts.count_realizations_per_bin(experts.get_exp('actual'), items=itembool))
            experts.calculate_weights(overshoot=overshoot, experts=exps, alpha=alphas[imax], calpower=calpower, items=itembool)
        
        # Get the scores for the final DM
        idx = experts.get_idx(exps[imax])
        results[tuple(seed_ids[i] for i in comb)] = (experts.info_total[idx], experts.info_real[idx], experts.calibration[idx])

        # experts.M.update(oldM)

        # Remove expert and recalculate scores
        # TODO: For performance, check if this step can be skipped. For now it is needed for consistency. If skipped, the commented rows below should be added
        experts.calculate_weights(
            overshoot=overshoot,
            alpha=alpha,
            calpower=calpower,
            experts=actual_experts
        )

    # Remove all experts
    for exp in totexps:
        experts.remove_expert(exp)

    # Recalculate original weights for actual experts
    # experts.calculate_weights(
    #     overshoot=overshoot,
    #     alpha=alpha,
    #     calpower=calpower,
    #     experts=actual_experts
    # )
        
    return results

def expert_robustness(min_exclude, max_exclude, experts, items, assessments, weight_type, overshoot, alpha=None, calpower=1.0, progress_func=None):
    """
    Calculate calibration and information scores by excluding experts.
    
    This function is generally similar to calculating a single decision maker
    for each combination of excluded experts.
    
    Parameters
    ----------
    min_exclude : int, optional
        Minimum number of items to exclude
    max_exclude : int
        Maximum number of items to exclude
    experts : anduryl.core.experts.Experts
        Expert class with the experts information and methods
    assessments : anduryl.core.assessments.Assessments
        Assessment class with the assessments information and methods
    items : anduryl.core.items.Items
        Item class with the items information and methods
    weight_type : str
        Weigth type: global, item, equal or user
    overshoot : float
        Intrinsic range, gives the total range per item
    alpha : float or Nonetype, optional
        Significance level, the minimum calibration value to take expert into account
    calpower : float, optional
        Calibration power, a factor to weigh the calibration to the information score, by default 1.0
    progress_func : function, optional
        Function to which the progress can be passed, for the GUI, by default None
    """

    if weight_type not in ['global', 'item']:
        raise KeyError(f'Robustness table can only be calculated for item or global weight (weight_type = \'{weight_type}\').')

    # Calculate information score per item and expert on beforehand
    actual_experts = experts.get_exp('actual')
    if max_exclude >= len(actual_experts):
        raise ValueError(f'Maximum number of excluded experts ({max_exclude}) can not be equal or greater than the number of experts ({len(actual_experts)}).')

    # Calculate original weights for actual experts
    experts.calculate_weights(
        overshoot=overshoot,
        alpha=alpha,
        calpower=calpower,
        experts=actual_experts
    )
    
    # Get the values for the items
    values = assessments.get_array(question_type='both', experts='actual')
    nexperts, npercentiles, nitems = values.shape
    
    # Scale values to log, if the background scale is log
    scale = items.scale
    for iq in range(nitems):
        if scale[iq] == 'log':
            use = items.use_quantiles[iq]
            values[:, use, iq] = np.log(values[:, use, iq])

    # Get combinations of experts to exclude
    combs = get_combinations(items=list(range(nexperts)), min_exclude=min_exclude, max_exclude=max_exclude)
    
    results = {}
    totexps = set()
    
    expidx = np.ones(nexperts, dtype=bool)
    
    # Loop trough all combinations of excluded experts
    for comb in combs:
        if progress_func is not None:
            progress_func()
        
        # Get selection as array and expert list
        expidx[:] = True
        expidx[list(comb)] = False
        exp_selection = [exp for i, exp in enumerate(actual_experts) if expidx[i]]

        # Get bounds for both seed and target questions
        qlower, qupper = assessments.get_bounds('both', overshoot=overshoot, experts=exp_selection)
        # Get CDF for selection of experts (and selected expert bounds)
        F_ex, all_answers = get_expert_CDFs(np.array(assessments.quantiles), items.use_quantiles, values[expidx, :, :], qlower, qupper)

        # Recalculate the information score, since selecting experts might change the bounds
        experts._information_score(exp_selection, overshoot=overshoot, bounds_for_experts=True)
        
        # Get weights for expert selection (based on newly calculated information scores)
        weights, alphas = experts.get_weights(weight_type=weight_type, experts=exp_selection, alpha=alpha)

        # Collect CDF
        DM = np.full((len(alphas), nitems, npercentiles + 2), np.nan)

        # Get DM for each item
        for iq in range(nitems):

            use = np.where(items.use_quantiles[iq])[0]
            item_quants = np.array(assessments.quantiles)[use]
                
            # Determine what experts have not answered the question
            no_answer = np.isnan(values[expidx, :, :][:, use, iq]).any(axis=1)
            use += 1
                        
            # Re-normalize weights without experts that have not answered
            if no_answer.any():
                weights[:, no_answer, iq] = 0.0
                weights[:, :, iq] /= weights[:, :, iq].sum(axis=1)[:, None]
            
            # Weight the experts, by getting the weighted sum (in product) of the quantiles
            F_DM = np.dot(F_ex[iq], weights[:, :, iq].T)
    
            # For each alpha (weight threshold), get the DM by interpolating the project quantiles
            # in the weighted CDF and all answers
            for ialpha in range(len(alphas)):
                # Determine decision makers for all alphas
                DM[ialpha, iq, 0] = qlower[iq]
                DM[ialpha, iq, -1] = qupper[iq]
                DM[ialpha, iq, use] = compiled_interp(item_quants, F_DM[:, ialpha], all_answers[iq])
            
                # If background scale is logaritmic, the values have to be converted back to their
                # original scale, so take the exponent.
                if scale[iq] == 'log':
                    DM[ialpha, iq, use] = np.exp(DM[ialpha, iq, use])

        # In case of optimisation, find the optimal alpha
        if alpha is None:
            # Now the DM is known for each question and weight threshold, find the optimal threshols
            # Get weight for each decision maker
            exps = [f'tmp{i}' for i in range(len(alphas))]
            totexps = totexps.union(set(exps))
            for (tmp_id, DMassessment) in zip(exps, DM):
                # Calculate weight of DM
                experts.add_expert(exp_id=tmp_id, exp_name=tmp_id, assessment=DMassessment, exp_type='dm', overwrite=True)
            # Calculate weights
            experts.calculate_weights(overshoot=overshoot, experts=exps, alpha=alphas, calpower=calpower)
            # Get the alpha for the highest weight
            imax = np.argmax(experts.weights[experts.get_idx(exps)])
            tmp_id = exps[imax]
            
        # Else there is only one DM, use this one.
        else:
            imax = 0
            tmp_id = 'tmp0'
            totexps = [tmp_id]
            # Add final expert and calculate weight
            experts.add_expert(exp_id=tmp_id, exp_name=tmp_id, assessment=DM[imax], exp_type='dm', overwrite=True)
            experts.calculate_weights(overshoot=overshoot, experts=[tmp_id], alpha=alphas[imax], calpower=calpower)
            
        # Calculate the scores for the final DM
        dmidx = experts.get_idx(tmp_id)
        experts._information_score(experts=exp_selection+[tmp_id], overshoot=overshoot, bounds_for_experts=True)
        results[tuple(actual_experts[i] for i in comb)] = experts.info_total[dmidx], experts.info_real[dmidx], experts.calibration[dmidx]
    
    # Remove all experts
    for exp in totexps:
        experts.remove_expert(exp)

    # Recalculate original weights for actual experts
    experts.calculate_weights(
        overshoot=overshoot,
        alpha=alpha,
        calpower=calpower,
        experts=actual_experts
    )
        
    return results
