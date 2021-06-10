import numpy as np

class Items:
    """
    Items class. Contain the properties for all items, as
    well as functions to add or remove items (questions) from the class.
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
        # Array with realizations (answers to questions)
        self.realizations = np.array([])
        # List with item ids
        self.ids = []
        # List with item scales
        self.scale = []
        # List with questions
        self.questions = []
        # List with excluded questions
        self.excluded = []
        # List with manual item bounds (limiting overshoot)
        self.item_bounds = np.array([], dtype=float)
        # List with manual item bounds (overriding general overshoot)
        self.item_overshoot = np.array([], dtype=float)
        # Array with percentiles to use in this assessment
        self.use_quantiles = np.array([], dtype=bool)

    def clear(self):
        """
        Clears all id's, scales and questions.
        """
        del self.ids[:]
        del self.scale[:]
        del self.questions[:]

    def initialize(self, nitems, nquantiles):
        """
        Initialize (empty) class. Allocates the lists
        and arrays given the number of seed and target questions
        
        Parameters
        ----------
        nitems : int
            Number of items
        """
        self.ids.extend([[] * nitems])
        self.scale.extend([[] * nitems])
        self.realizations.resize(nitems, refcheck=False)
        self.item_bounds.resize((nitems, 2), refcheck=False)
        self.item_overshoot.resize((nitems, 2), refcheck=False)
        self.use_quantiles.resize((nitems, nquantiles), refcheck=False)

    def get_idx(self, question_type='both', where=False):
        """
        Returns the index of a question type: seed, target or both
        
        Parameters
        ----------
        question_type : str, optional
            Question type to return (seed, target or both), by default 'both'
        where : bool, optional
            Whether to return the indices instead of a boolean array, by default False
        
        Returns
        -------
        np.ndarray
            Array with position of questions as booleans or indices
        """
        if question_type == 'seed':
            idx = ~np.isnan(self.realizations)
        elif question_type == 'target':
            idx = np.isnan(self.realizations)
        elif question_type == 'both':
            idx = np.ones(len(self.realizations), dtype=bool)
        else:
            raise KeyError(question_type)
        if where:
            idx = np.where(idx)[0]
        return idx
        
    def add_item(self, item_id):
        """
        Add item to list, also assigns a default value
        for the scale (uniform) and adds an item to the question list,
        realizations array, assessment array and infoscore per item array.
        
        Parameters
        ----------
        item_id : str
            Item (question) id
        """
        self.ids.append(item_id)
        self.scale.append('uni')
        self.questions.append('')

        nitems = len(self.realizations)+1
        
        # Add realization (default np.nan)
        self.realizations.resize(nitems, refcheck=False)
        self.realizations[-1] = np.nan

        # Add item bounds and item_overshoot, defaults to (np.nan, np.nan)
        for arr in [self.item_bounds, self.item_overshoot]:
            arr.resize((nitems, 2), refcheck=False)
            arr[-1, :] = [np.nan, np.nan]
        
        self.use_quantiles.resize((nitems, len(self.project.assessments.quantiles)), refcheck=False)
        self.use_quantiles[-1, :] = True
        
        # Add item
        shape = self.project.experts.info_per_var.shape
        vals = self.project.experts.info_per_var.copy()
        self.project.experts.info_per_var.resize((shape[0], shape[1]+1), refcheck=False)
        self.project.experts.info_per_var[:, :-1] = vals[:, :]

        # Add to assessments
        arr = self.project.assessments.array
        current_vals = arr.copy()
        arr.resize(arr.shape[0], arr.shape[1], arr.shape[2]+1, refcheck=False)
        arr[:, :, :-1] = current_vals
        arr[:, :, -1] = np.nan

    def move_item(self, item_id, newpos):
        """
        Move item to new position in list
        
        Parameters
        ----------
        item_id : str
            Item (question) id
        newpos : int
            Index of new position
        """
        oldpos = self.ids.index(item_id)
        order = list(range(len(self.ids)))
        order.remove(oldpos)
        # Insert index of old position in new position
        order.insert(newpos, oldpos)
        order = np.array(order)
        
        # Rearrange lists and 1d arrays
        for lst in [self.ids, self.scale, self.questions, self.realizations, self.item_bounds, self.item_overshoot, self.use_quantiles]:
            lst[:] = [lst[i] for i in order]
        
        # Reaarange assessments
        self.project.assessments.array[:, :, :] = self.project.assessments.array[:, :, order]
        # Reaarange information score per variable
        self.project.experts.info_per_var[:, :] = self.project.experts.info_per_var[:, order]
        
    def remove_item(self, item_id):
        """
        Removes an item from the class. Removes the item from the id's,
        scale, questions, realizations, assessesments and information score per item
        
        Parameters
        ----------
        item_id : str
            Item (question) id
        """
        # Check if present
        if item_id not in self.ids:
            raise KeyError(f'Item "{item_id}" not in item ids.')
        
        # Get index
        idx = self.ids.index(item_id)
        # Remove from ids and names
        del self.scale[idx]
        del self.questions[idx]
        del self.ids[idx]
                
        # Remove from 1d arrays
        keep = np.ones(len(self.realizations), dtype=bool)
        keep[idx] = False
        keep = np.where(keep)[0]

        # Resize all arrays over axis 0 (items are on the first axis for these arrays)
        arrays = [
            (self.realizations, 0),
            (self.item_bounds, 0),
            (self.item_overshoot, 0),
            (self.use_quantiles, 0),
            (self.project.experts.info_per_var, -1),
            (self.project.assessments.array, -1),
        ]

        # Take items to keep, resize array and assign without change the memory id
        for arr, axis in arrays:
            vals = np.take(arr, keep, axis=axis)
            arr.resize(vals.shape, refcheck=False)
            arr[:] = vals

    def as_dict(self, orient='columns'):
        """
        Returns an overview of the item data as a Python dictionary.
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

        lists = (self.ids, self.scale, self.realizations, self.questions)
        
        dct = {}
        for ID, scale, realization, question in zip(*lists):
            dct[ID] = {
                'Scale': scale,
                'Realization': realization,
                'Question': question
            }
        
        if orient == 'columns':
            # Transpose
            keys = dct[ID].keys()
            dct = {key:{k:dct[k][key] for k in dct if key in dct[k]} for key in keys}

        return dct
