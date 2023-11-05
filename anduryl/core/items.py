import numpy as np
from anduryl.model.assessment import Assessment, ExpertAssessment


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
        self.scales = []
        # List with questions
        self.questions = []
        # List with units
        self.units = []
        # List with excluded questions
        self.excluded = []
        # List with manual item bounds (limiting overshoot)
        self.bounds = np.zeros(shape=(0, 2), dtype=float)
        # List with manual item bounds (overriding general overshoot)
        self.overshoots = np.zeros(shape=(0, 2), dtype=float)
        # Array with percentiles to use in this assessment
        self.use_quantiles = np.array([], dtype=bool)

    def clear(self):
        """
        Clears all id's, scales and questions.
        """
        del self.ids[:]
        del self.scales[:]
        del self.questions[:]
        del self.units[:]

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
        self.units.extend([[""] * nitems])
        self.scales.extend([[] * nitems])
        self.realizations.resize(nitems, refcheck=False)
        self.bounds.resize((nitems, 2), refcheck=False)
        self.overshoots.resize((nitems, 2), refcheck=False)
        self.use_quantiles.resize((nitems, nquantiles), refcheck=False)

    def get_idx(self, question_type="both", where=False):
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
        if question_type == "seed":
            idx = ~np.isnan(self.realizations)
        elif question_type == "target":
            idx = np.isnan(self.realizations)
        elif question_type == "both":
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
        self.scales.append("uni")
        self.questions.append("")
        self.units.append("")

        nitems = len(self.realizations) + 1

        # Add realization (default np.nan)
        self.realizations.resize(nitems, refcheck=False)
        self.realizations[-1] = np.nan

        # Add item bounds and overshoots, defaults to (np.nan, np.nan)
        for arr in [self.bounds, self.overshoots]:
            arr.resize((nitems, 2), refcheck=False)
            arr[-1, :] = [np.nan, np.nan]

        self.use_quantiles.resize((nitems, len(self.project.assessments.quantiles)), refcheck=False)
        self.use_quantiles[-1, :] = True

        # Add item
        shape = self.project.experts.info_per_var.shape
        vals = self.project.experts.info_per_var.copy()
        self.project.experts.info_per_var.resize((shape[0], shape[1] + 1), refcheck=False)
        self.project.experts.info_per_var[:, :-1] = vals[:, :]

        # Add to assessments
        arr = self.project.assessments.array
        current_vals = arr.copy()
        arr.resize(arr.shape[0], arr.shape[1], arr.shape[2] + 1, refcheck=False)
        arr[:, :, :-1] = current_vals
        arr[:, :, -1] = np.nan

        # Add estimates
        quantiles_arr = np.array(self.project.assessments.quantiles)
        for expertid in self.project.experts.ids:
            self.project.assessments.estimates[expertid][item_id] = ExpertAssessment(
                quantiles=quantiles_arr[self.use_quantiles[-1, :]],
                values=[np.nan] * self.use_quantiles[-1, :].sum(),
                expertid=expertid,
                itemid=item_id,
                scale="uni",
                observer=self.project.assessments.update_array_value,
            )

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
        for lst in [
            self.ids,
            self.scales,
            self.questions,
            self.units,
            self.realizations,
            self.bounds,
            self.overshoots,
            self.use_quantiles,
        ]:
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
        del self.scales[idx]
        del self.questions[idx]
        del self.units[idx]
        del self.ids[idx]

        # Remove from excluded list
        if item_id in self.excluded:
            self.excluded.remove(item_id)

        # Remove from 1d arrays
        keep = np.ones(len(self.realizations), dtype=bool)
        keep[idx] = False
        keep = np.where(keep)[0]

        # Resize all arrays over axis 0 (items are on the first axis for these arrays)
        arrays = [
            (self.realizations, 0),
            (self.bounds, 0),
            (self.overshoots, 0),
            (self.use_quantiles, 0),
            (self.project.experts.info_per_var, -1),
            (self.project.assessments.array, -1),
        ]

        # Take items to keep, resize array and assign without change the memory id
        for arr, axis in arrays:
            vals = np.take(arr, keep, axis=axis)
            arr.resize(vals.shape, refcheck=False)
            arr[:] = vals

        # Remove estimates
        for expertid in self.project.experts.ids:
            del self.project.assessments.estimates[expertid][item_id]

    def as_dict(self, orient="columns", lists=["ids", "scales", "realizations", "questions", "units"]):
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

        if orient not in ["columns", "index"]:
            raise KeyError(f"Orient {orient} should be 'columns' or 'index'.")

        list_objs = (getattr(self, "ids"),)
        for l in lists:
            if l == "ids":
                continue
            list_objs += (getattr(self, l),)

        conv_dict = {
            "ids": "id",
            "scales": "scale",
            "realizations": "realization",
            "questions": "question",
            "units": "unit",
            "overshoots": "overshoots",
            "bounds": "bounds",
        }

        tuples = ["overshoots", "bounds"]

        # Create the total dict
        dct = {}
        for row in zip(*list_objs):
            # Per item, create a dictionary
            rowdct = {}
            # Add all lists
            for l, item in zip(lists[1:], row[1:]):
                rowdct[conv_dict[l]] = tuple(item) if l in tuples else item
            # Get the id, and add to total dict
            ID = row[0]
            dct[ID] = rowdct

        if orient == "columns":
            # Transpose
            keys = dct[ID].keys()
            dct = {key: {k: dct[k][key] for k in dct if key in dct[k]} for key in keys}

        return dct
