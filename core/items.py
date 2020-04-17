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
        self.realizations = np.array([])
        self.ids = []
        self.scale = []
        self.questions = []
        self.excluded = []

    def clear(self):
        """
        Clears all id's, scales and questions.
        """
        del self.ids[:]
        del self.scale[:]
        del self.questions[:]

    def initialize(self, nitems):
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
        self.realizations.resize(len(self.realizations)+1, refcheck=False)
        self.realizations[-1] = np.nan

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
        vals = self.realizations[keep]
        self.realizations.resize(len(vals), refcheck=False)
        self.realizations[:] = vals

        # Info per var
        vals = self.project.experts.info_per_var[:, keep]
        self.project.experts.info_per_var.resize(vals.shape, refcheck=False)
        self.project.experts.info_per_var[:] = vals
        
        # Assessments
        vals = self.project.assessments.array[:, :, keep].copy()
        self.project.assessments.array.resize(vals.shape, refcheck=False)
        self.project.assessments.array[:, :, :] = vals
