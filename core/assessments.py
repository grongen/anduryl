# -*- coding: utf-8 -*-
"""
Created on Tue Nov 27 15:21:11 2018

@author: rongen
"""


import numpy as np
        
class Assessment:
    """
    Assessment class. Contains the assessments for all experts and all items.
    """

    def __init__(self, project):
        """
        Constructor
        """
        self.project = project
        self.quantiles = [0.05, 0.5, 0.95]
        self.array = np.zeros((0, len(self.quantiles), 0))
        self.calculate_binprobs()
        self.full_cdf = {}

    def calculate_binprobs(self):
        """
        Calculate probabilities in between quantiles
        """
        if self.quantiles:
            self.binprobs = np.concatenate([[self.quantiles[0]], np.diff(self.quantiles), [1.0-self.quantiles[-1]]])
        else:
            self.binprobs = None

    def add_quantile(self, quantile):
        """
        Add a quantile to the project. Adds the quantile and allocates the space in the array.
        
        Parameters
        ----------
        quantile : float
            Quantile to add
        """
        if not 0.0 < quantile < 1.0:
            raise ValueError('Quantile should be > 0.0 and < 1.0')

        if quantile in self.quantiles:
            raise ValueError(f'Quantile "{quantile}" is already present.')

        # Get position of new quantile
        pos = ([i for i, q in enumerate(self.quantiles) if quantile < q] + [len(self.quantiles)])[0]
        self.project.assessments.quantiles.insert(pos, quantile)

        # Assessments
        values = self.project.assessments.array.copy()
        shape = list(values.shape)
        shape[1] += 1
        idx = np.ones(shape[1], dtype=bool)
        idx[pos] = False

        # Adjust array size and refill values
        self.array.resize(shape, refcheck=False)
        self.array[:, idx, :] = values[:, :, :]
        self.array[:, ~idx, :] = np.nan
        self.calculate_binprobs()

        # Adjust array of use_quantiles in items class
        self.project.items.use_quantiles.resize((self.array.shape[2], len(self.quantiles)), refcheck=False)
        self.project.items.use_quantiles[:, idx] = values[:, :]
        self.project.items.use_quantiles[:, ~idx] = False
        

    def remove_quantile(self, quantile):
        """
        Removes a quantile from the project. Removes the quantile and removes
        the values from the assessment array.
        
        Parameters
        ----------
        quantile : float
            Quantile to remove
        """
        if quantile not in self.quantiles:
            raise ValueError(f'Quantile "{quantile}" is not present.')

        # Get position of new quantile
        pos = self.quantiles.index(quantile)
        del self.project.assessments.quantiles[pos]

        # Assessments
        values = self.project.assessments.array.copy()
        shape = list(values.shape)
        keep = np.ones(shape[1], dtype=bool)
        keep[pos] = False
        shape[1] -= 1

        # Adjust array size and refill values
        self.array.resize(shape, refcheck=False)
        self.array[:, :, :] = values[:, keep, :]

        # Adjust array of use_quantiles in items class
        values = self.project.items.use_quantiles.copy()
        self.project.items.use_quantiles.resize((self.array.shape[2], len(self.quantiles)), refcheck=False)
        self.project.items.use_quantiles[:, :] = values[:, keep]


        self.calculate_binprobs()

    def clear(self):
        """
        Deletes all quantiles
        """
        del self.quantiles[:]

    def initialize(self, nexperts, nitems, nquantiles):
        """
        Resizes the assessment array with the given dimensions
        
        Parameters
        ----------
        nexperts : int
            Number of experts
        nitems : int
            Number of items
        nquantiles : int
            Number of quantiles
        """
        self.array.resize((nexperts, nquantiles, nitems), refcheck=False)
        
    def get_array(self, question_type='both', experts=None):
        """
        Return the assessments as 3D-array with dimensions:
        (Nexperts, Nquantiles, Nquestions)

        Parameters
        ----------
        question_type: str, optional
            seed, target or both, by default 'both'
        experts: list or str
            Expert(s) for which to return the assessments
        
        Returns
        -------
        np.ndarray
            Array with assessments
        """
        # Get index for experts
        idx = self.project.experts.get_idx(experts)
        
        # Get values and reshape
        seedidx = ~np.isnan(self.project.items.realizations)
        if question_type == 'both':
            return self.array[idx]
        elif question_type == 'seed':
            return self.array[idx][:, :, seedidx]
        elif question_type == 'target':
            return self.array[idx][:, :, ~seedidx]

    def get_bounds(self, question_type='both', overshoot=0.0, experts=None):
        """
        Return lower and upper bounds for each question given
        the question type. Overshoot can be added by specifying overshoot (k).

        Parameters
        ----------
        question_type : str
            both, seed or target, default 'both'
        overshoot : float, optional
            overshoot, default 0.0
        experts: list or str
            Expert(s) for which to return the bounds
        
        Returns
        -------
        tuple
            Array with lower bounds and array with upper bounds
        """
        # Get selection of questions from dataframe
        values = self.get_array(question_type=question_type, experts=experts)
        if values.shape[0] == 0:
            return np.array([]), np.array([])
        
        # Get bounds per question
        lower = np.nanmin(values[:, :, :], axis=(0, 1))
        upper = np.nanmax(values[:, :, :], axis=(0, 1))
        
        # If seed questions, combine with realisations
        realizations = self.project.items.realizations[:]
        nseed = len(realizations)

        seedidx = ~np.isnan(realizations)
        realizations = realizations[seedidx]
        if question_type == 'seed':
            lower = np.minimum(lower, realizations)
            upper = np.maximum(upper, realizations)
            scale = self.project.items.scale[seedidx]

        elif question_type == 'target':
            scale = self.project.items.scale[~seedidx]

        else:
            lower[seedidx] = np.minimum(lower[seedidx], realizations)
            upper[seedidx] = np.maximum(upper[seedidx], realizations)
            scale = self.project.items.scale

        # Add overshoot
        if overshoot > 0.0:
            # Get log inndices
            islog = [i for i, sc in enumerate(scale) if sc == 'log']
            if len(islog):
                lower[islog] = np.log(lower[islog])
                upper[islog] = np.log(upper[islog])
            
            maxrange = upper - lower
            lower -= overshoot * maxrange
            upper += overshoot * maxrange
                
        return lower, upper

    def as_dict(self, orient='columns'):
        """
        Returns an overview of the assessments for all experts
        and item as a Python dictionary.
        The result can easily be converted to a pandas DataFrame with
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

        if orient not in ['columns', 'index']:
            raise KeyError(f"Orient {orient} should be 'columns' or 'index'.")

        nexp, nquant, nitem = self.array.shape
        table = np.swapaxes(self.array, 1, 2).reshape((nexp * nitem, nquant))

        index = [(exp, item) for exp, item in zip(np.repeat(self.project.experts.ids, nitem), np.tile(self.project.items.ids, nexp))]
        quantiles = self.project.assessments.quantiles
        
        if orient == 'index':
            dct = {idx: {q: val for q, val in zip(quantiles, row)} for idx, row in zip(index, table)}
        
        elif orient == 'columns':
            dct = {q: {idx: row for idx, row in zip(index, table[:, i])} for i, q in enumerate(quantiles)}
            
        return dct


