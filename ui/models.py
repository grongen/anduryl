from PyQt5 import Qt, QtCore, QtGui, QtWidgets
import numpy as np
from operator import itemgetter
from anduryl.ui.dialogs import NotificationDialog
from matplotlib import cm


def strformat(item):
    """
    String formatter

    Parameters
    ----------
    item : str or int or float
        Item to be converted to formatted string

    Returns
    -------
    str
        Formatted string
    """
    return item if isinstance(item, str) else "{:.4g}".format(item).replace("nan", "")


class ItemDelegate(QtWidgets.QItemDelegate):
    """
    Item delegate where data can be changed.
    """

    def __init__(self, model):
        """Constructor"""
        super(ItemDelegate, self).__init__()
        self.model = model

    def setEditorData(self, editor, index):
        """Function to set data"""
        editor.setText(self.model.data(index))


class ArrayModel(QtCore.QAbstractTableModel):
    """
    Generic Array model
    Class to populate a table view with an array
    """

    def __init__(self, array, labels, coldim, rowdim, index_names, index, selector=None):
        """Constructor"""
        # Inherit
        QtCore.QAbstractTableModel.__init__(self)

        # Add parameters
        self.coldim = coldim
        self.rowdim = rowdim
        self.array = array
        self.labels = labels
        self.show_index = index
        self.index_names = index_names
        self.selector = selector

        # Check label dimensions
        for i, label in enumerate(labels):
            if not len(label) == self.array.shape[i]:
                raise ValueError(
                    f"Number of given labels ({len(label)}) does not match the array size ({self.array.shape[i]})."
                )

        # If index == true, the index is used to show the index labels
        # If false, the index is shown as column(s), which is obligated
        # for multi-indexes (arrays with 3+ dimensions)
        if self.show_index:
            self.nrowdim = 0
        else:
            self.nrowdim = len(rowdim)

        # Parameters for coloring
        self.colored = False

    def rowCount(self, parent):
        """Get the number of visible rows"""
        count = 1
        for dim in self.rowdim:
            count *= self.array.shape[dim] if self.selector is None else self.selector.shape[dim]
        return count

    def columnCount(self, parent):
        """Get the number of visible columns"""
        return self.array.shape[self.coldim] + self.nrowdim

    def get_array_index(self, row, col):
        """Method to get the value from the ND-array, given row and column"""
        # Get the unraveled row index.
        shape = self.array.shape if self.selector is None else self.selector.shape
        unravel_row = np.unravel_index(row, tuple(shape[i] for i in self.rowdim))

        # Get item index
        idx = [0] * (len(self.rowdim) + 1)
        for i, dim in enumerate(self.rowdim):
            idx[dim] = unravel_row[i]
        idx[self.coldim] = col - self.nrowdim

        # If a selection is shown the index has to be compensated for that
        if self.selector is not None and self.selector.dim != -1:
            idx[self.selector.dim] = self.selector.index

        return tuple(idx)

    def get_list_label(self, row, col):
        """
        Method to get the label (string) of the index lists

        Parameters
        ----------
        row : int
            Row index
        col : int
            Column index

        Returns
        -------
        str
            Get label for the array dimension, given the table row and column
        """

        shape = self.array.shape if self.selector is None else self.selector.shape
        unravel_row = np.unravel_index(row, tuple(shape[i] for i in self.rowdim))
        dim = self.rowdim[col]
        # Selection, return
        if dim == self.selector.dim:
            label = self.labels[dim][self.selector.index]
        else:
            label = self.labels[dim][unravel_row[col]]

        return label

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        Method to set the data to a cell. Sets value, alignment and color

        Parameters
        ----------
        index : int
            Index object with row and column
        role : Qt.DisplayRole, optional
            Property of data to display, by default QtCore.Qt.DisplayRole

        Returns
        -------
        QtCore.QVariant
            Property of data displayed
        """
        if not index.isValid():
            return None

        # Get index
        row, col = index.row(), index.column()

        # Set value as string
        if (role == QtCore.Qt.DisplayRole) or (role == QtCore.Qt.ToolTipRole):
            if col < self.nrowdim:
                # Get label
                return self.get_list_label(row, col)
            else:
                return strformat(self.array[self.get_array_index(row, col)])

        # Set alignment
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.QVariant(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        # Set colors
        if self.colored and role == QtCore.Qt.BackgroundColorRole:
            if col < self.nrowdim:
                return None
            # Get value
            color = self.colorpicker(self.get_array_index(row, col))
            # Get color
            color = [int(i * 255) for i in color][:3]
            # Define color
            bgColor = QtGui.QColor(*color, 100)

            return QtCore.QVariant(QtGui.QColor(bgColor))

    def headerData(self, rowcol, orientation, role):
        """
        Method to get header (index and columns) data
        """
        # Index
        if self.show_index and orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self.labels[self.rowdim[0]][rowcol]

        # Columns
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if rowcol < self.nrowdim:
                # 'index' columns
                return self.index_names[rowcol]
            else:
                # value columns
                return str(self.labels[self.coldim][rowcol - self.nrowdim])


class Selector:
    """
    Class to keep track of the selection of an array that is shown
    by the UI.
    """

    def __init__(self, array):
        """Constructer

        Parameters
        ----------
        array : np.ndarray
            Numpy array from which selection can be made
        """

        self.index = -1
        self.dim = -1
        self.shape = list(array.shape)
        self.array = array

    def update(self, dim=None, index=None):
        """
        Update the parts of the array that are selected.

        Parameters
        ----------
        dim : int, optional
            Array dimension to apply selection, by default None
        index : int, optional
            Index of the dimension that is shown, by default None
        """

        # Update the shape of the array
        self.update_shape()

        # If a dimension is given
        if dim is not None:
            # Set dimension, the index (also given) and change the pseudoshape in that dimension
            self.dim = dim
            self.index = index
            self.shape[dim] = 1
        else:
            # If no dimension is given, reset to the original shape
            self.dim = -1
            self.index = -1

    def update_shape(self):
        """
        Update the shape of the array
        When the array changes, the selector will still show the right items
        """
        for i, size in enumerate(self.array.shape):
            self.shape[i] = size


class AssessmentArrayModel(ArrayModel):
    """
    Generic Array model
    Class to populate a table view with an array
    """

    def __init__(self, parentwidget):
        """Constructor"""
        # Inherit
        project = parentwidget.project

        super(AssessmentArrayModel, self).__init__(
            array=project.assessments.array,
            labels=[project.experts.ids, project.assessments.quantiles, project.items.ids],
            coldim=1,
            rowdim=(0, 2),
            index_names=["Expert", "Item"],
            index=False,
            selector=Selector(project.assessments.array),
        )
        self.project = project
        self.parentwidget = parentwidget
        self.cmap = cm.get_cmap("RdBu")

    def flags(self, index):
        """
        Get cell properties (flags) given the index
        """

        col = index.column()
        row = index.row()

        fl = QtCore.Qt.NoItemFlags
        if index.isValid():
            fl |= Qt.Qt.ItemIsEnabled | Qt.Qt.ItemIsSelectable | Qt.Qt.ToolTip
            arridx = self.get_array_index(row, col)
            if not (col < self.nrowdim or arridx[0] in self.project.experts.decision_makers):
                fl |= Qt.Qt.ItemIsEditable

        return fl

    def _check_monotonous(self, idx, value):
        """
        Method to check if given quantile is in between existing quantiles
        """
        above = self.array[idx[0], idx[1] + 1, idx[2]] if idx[1] < self.array.shape[1] - 1 else np.nan
        below = self.array[idx[0], idx[1] - 1, idx[2]] if idx[1] > 0 else np.nan

        # Dont check
        if np.isnan(above) and np.isnan(below):
            return True

        # Check above
        elif np.isnan(below):
            if above <= value:
                NotificationDialog(f"Value should be less than {above:.4g}.")
                return False

        # Check below
        elif np.isnan(above):
            if below >= value:
                NotificationDialog(f"Value should be greater than {below:.4g}.")
                return False

        # Check both
        else:
            if not below < value < above:
                NotificationDialog(f"Value should be in between {below:.4g} and {above:.4g}.")
                return False

        return True

    def setData(self, index, value, role=Qt.Qt.EditRole):
        """
        Method to set data to cell. Changes the value in the array too.
        The value is checked for beigin in between other percentiles.
        """
        col = index.column()
        row = index.row()

        if value == "":
            self.array[self.get_array_index(row, col)] = np.nan
            return True

        # Check if the value is between the percentiles
        idx = self.get_array_index(row, col)

        # Check below
        valid = self._check_monotonous(idx, float(value))
        if not valid:
            return True

        if col >= self.nrowdim:
            self.array[idx] = float(value)

        # Update range if value has changed
        self.update_range()

        # Next column after entering value
        newcol = col + 1
        newrow = row
        if newcol >= self.nrowdim + len(self.labels[self.coldim]):
            newcol = self.nrowdim
            newrow = row + 1
        self.parentwidget.table.setCurrentIndex(self.index(newrow, newcol))

        # Unsaved changes
        self.parentwidget.mainwindow.setWindowModified(True)

        return True

    def update_range(self):
        """
        Method to update the used color range.
        This method is called from the project signal "update_color_range"

        Should update when:
        - Assessments values are changed
        - Experts are added or removed
        - Items are added or removed
        - New DM is calculated (possibly overshoot had changed)
        """
        # Get lower and upper bounds and realizations
        self.lower, self.upper = self.project.assessments.get_bounds("both")
        if np.isnan(self.lower).all():
            self.midpoint = np.full_like(self.lower, np.nan)
            return None

        realiz = self.project.items.realizations
        nrealiz = len(realiz)
        self.midpoint = np.zeros_like(self.lower)
        self.midpoint[:nrealiz] = realiz

        arr = self.project.assessments.get_array("target")
        for irel, iabs in enumerate(np.where(np.isnan(self.project.items.realizations))[0]):
            if self.project.items.scale[iabs] == "log":
                self.midpoint[iabs] = np.exp(np.nanmedian(np.log(arr[:, :, irel])))
            else:
                self.midpoint[iabs] = np.nanmedian(arr[:, :, irel])

    def colorpicker(self, idx):
        """Returns a number (0-1) for assigning a color to the cell"""
        value = self.array[idx]
        if np.isnan(value):
            return (0.5, 0.5, 0.5)

        dimidx = idx[2]
        xp = [self.lower[dimidx], self.midpoint[dimidx], self.upper[dimidx]]
        if np.isnan(xp).any():
            return (0.5, 0.5, 0.5)
        if self.project.items.scale[dimidx] == "log":
            value = np.interp(np.log(value), np.log(xp), [0, 0.5, 1.0])
        else:
            value = np.interp(value, xp, [0, 0.5, 1.0])
        return self.cmap(value)


class ListsModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """

    def __init__(self, lists, labels):
        QtCore.QAbstractTableModel.__init__(self)
        self.lists = lists
        self.labels = labels
        self.leftalign = []

        # Check label dimensions
        if len(lists) != len(labels):
            raise ValueError(f"Requires an equal number of lists ({len(lists)}) and labels ({len(labels)}).")

    def rowCount(self, parent=None):
        """Returns number of rows in table."""
        return len(self.lists[0])

    def columnCount(self, parent=None):
        """Returns number of columns in table."""
        return len(self.lists)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        Method to set the data to a cell. Sets value, alignment and color

        Parameters
        ----------
        index : int
            Index object with row and column
        role : Qt.DisplayRole, optional
            Property of data to display, by default QtCore.Qt.DisplayRole

        Returns
        -------
        QtCore.QVariant
            Property of data displayed
        """
        if not index.isValid():
            return None

        # Get number from lists
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            lst = self.lists[index.column()]

            if row < len(lst):
                item = lst[index.row()]
                if isinstance(item, str):
                    return item
                else:
                    return strformat(item)

        # Alignment
        elif role == QtCore.Qt.TextAlignmentRole:
            if index.column() in self.leftalign:
                return QtCore.QVariant(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            else:
                return QtCore.QVariant(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

    def headerData(self, rowcol, orientation, role):
        """
        Method to get header (index and columns) data
        """
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return str(self.labels[rowcol])


class ItemsListsModel(ListsModel):
    """
    Class to populate a table view with several lists related to the items
    """

    def __init__(self, parentwidget):
        """
        Constructor

        Parameters
        ----------
        parentwidget : Table widget
            Widget of which this table model is part.
        """
        self.parentwidget = parentwidget
        self.mainwindow = parentwidget.mainwindow
        self.project = parentwidget.mainwindow.project

        super(ItemsListsModel, self).__init__(
            lists=[
                self.project.items.ids,
                self.project.items.realizations,
                self.project.items.scale,
                self.project.items.questions,
            ],
            labels=["ID", "Realization", "Scale", "Question"],
        )

        self.editable = [True, True, True, True]

    def flags(self, index):
        """
        Returns flags (properties) for a certain cell, based on the index

        Parameters
        ----------
        index : ModelIndex
            index of the cell

        Returns
        -------
        flags
            Properties of the cell
        """
        col = index.column()

        fl = QtCore.Qt.NoItemFlags
        if index.isValid():
            fl |= Qt.Qt.ItemIsEnabled | Qt.Qt.ItemIsSelectable
            if self.editable[col]:
                fl |= Qt.Qt.ItemIsEditable
            if col == 0:
                fl |= QtCore.Qt.ItemIsUserCheckable
        return fl

    def setData(self, index, value, role=Qt.Qt.EditRole):
        """
        Method to set data to cell. Changes the value in the list or array
        The value is checked for beigin in between other percentiles.
        """
        if not index.isValid():
            return False

        col = index.column()
        row = index.row()

        if role == QtCore.Qt.CheckStateRole and col == 0:
            self.layoutAboutToBeChanged.emit()
            self.parentwidget.toggle_item(self.project.items.ids[row])
            self.layoutChanged.emit()
            return True

        if self.labels[col] == "ID" and value == "":
            NotificationDialog(f"An empty item ID is not allowed.")
            return False

        if self.labels[col] == "ID" and value in self.lists[col]:
            NotificationDialog(f"Item ID is already present. Pick a unique ID.")
            return False

        elif self.labels[col] == "Scale" and value.lower() not in ["log", "uni"]:
            NotificationDialog(f"Scale should be either 'log' or 'uni'.")
            return False

        # If empty value is given
        current = self.lists[col][row]
        if isinstance(current, float):
            self.lists[col][row] = np.nan if value == "" else float(value)
        else:
            self.lists[col][row] = value

        # If a realization is changed, update the color ranges
        if self.labels[col] in ["Realization", "Scale"]:
            self.mainwindow.signals.update_color_range()
        # Item id changed, update the Id's in the other views and items
        elif self.labels[col] == "ID":
            self.mainwindow.signals.update_ids()

        # Unsaved changes
        self.mainwindow.setWindowModified(True)

        # Skip row after entering value
        self.parentwidget.table.setCurrentIndex(self.index(row + 1, col))

        return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        Method to set the data to a cell. Sets value, alignment and color

        Parameters
        ----------
        index : int
            Index object with row and column
        role : Qt.DisplayRole, optional
            Property of data to display, by default QtCore.Qt.DisplayRole

        Returns
        -------
        QtCore.QVariant
            Property of data displayed
        """

        excluded = self.project.items.ids[index.row()] in self.project.items.excluded

        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            return QtCore.Qt.Unchecked if excluded else QtCore.Qt.Checked

        elif role == QtCore.Qt.ForegroundRole and excluded:
            return QtGui.QBrush(QtCore.Qt.gray)

        else:
            return super(ItemsListsModel, self).data(index, role)


class ItemsBoundsModel(ListsModel):
    """
    Class to populate a table view with several lists related to the items
    """

    def __init__(self, parentwidget):
        """
        Constructor

        Parameters
        ----------
        parentwidget : Table widget
            Widget of which this table model is part.
        """
        self.parentwidget = parentwidget
        self.mainwindow = parentwidget.mainwindow
        self.project = parentwidget.mainwindow.project

        quantiles = self.project.assessments.quantiles
        nquantiles = len(quantiles)

        super().__init__(
            lists=[
                self.project.items.item_bounds[:, 0],
                self.project.items.item_bounds[:, 1],
                self.project.items.item_overshoot[:, 0],
                self.project.items.item_overshoot[:, 1],
            ]
            + [self.project.items.use_quantiles[:, i] for i in range(nquantiles)],
            labels=["Lower\nbounds", "Upper\nbounds", "Lower\novershoot", "Upper\novershoot"] + quantiles,
        )

        self.indexlabels = self.project.items.ids
        self.editable = [True, True, True, True] + [False] * nquantiles
        self.checkable = [False, False, False, False] + [True] * nquantiles

    def flags(self, index):
        """
        Returns flags (properties) for a certain cell, based on the index

        Parameters
        ----------
        index : ModelIndex
            index of the cell

        Returns
        -------
        flags
            Properties of the cell
        """
        col = index.column()

        fl = QtCore.Qt.NoItemFlags
        if index.isValid():
            fl |= Qt.Qt.ItemIsEnabled
            if not self.checkable[col]:
                fl |= Qt.Qt.ItemIsSelectable
            if self.editable[col]:
                fl |= Qt.Qt.ItemIsEditable
            # elif self.checkable[col]:
            # fl |= QtCore.Qt.ItemIsUserCheckable
        return fl

    def setData(self, index, value, role=Qt.Qt.EditRole):
        """
        Method to set data to cell. Changes the value in the list or array
        The value is checked for beigin in between other percentiles.
        """
        if not index.isValid():
            return False

        col = index.column()
        row = index.row()

        # elif self.labels[col] == 'Scale' and value.lower() not in ['log', 'uni']:
        #     NotificationDialog(f'Scale should be either \'log\' or \'uni\'.')
        #     return False

        # Change empty values for NaN, if a float was previously present
        current = self.lists[col][row]
        if isinstance(current, float):
            self.lists[col][row] = np.nan if value == "" else float(value)
        else:
            self.lists[col][row] = value

        # # If a realization is changed, update the color ranges
        # if self.labels[col] in ['Realization', 'Scale']:
        #     self.mainwindow.signals.update_color_range()
        # # Item id changed, update the Id's in the other views and items
        # elif self.labels[col] == 'ID':
        #     self.mainwindow.signals.update_ids()

        # Unsaved changes
        self.mainwindow.setWindowModified(True)

        # Skip row after entering value
        # self.parentwidget.table.setCurrentIndex(self.index(row+1, col))

        return True

    # def data(self, index, role=QtCore.Qt.DisplayRole):
    #     """
    #     Method to set the data to a cell. Sets value, alignment and color

    #     Parameters
    #     ----------
    #     index : int
    #         Index object with row and column
    #     role : Qt.DisplayRole, optional
    #         Property of data to display, by default QtCore.Qt.DisplayRole

    #     Returns
    #     -------
    #     QtCore.QVariant
    #         Property of data displayed
    #     """

    #     col = index.column()
    #     row = index.row()
    #     # if role == QtCore.Qt.CheckStateRole and self.checkable[col]:
    #         # return QtCore.Qt.Checked if self.lists[col][row] else QtCore.Qt.Unchecked
    #     # print(role)
    #     # if self.checkable[col] and role == QtCore.Qt.:
    #     if self.checkable[col] and role == QtCore.Qt.DisplayRole:
    #         return ''
    #     # else:
    #     return super(ItemsBoundsModel, self).data(index, role)

    def headerData(self, rowcol, orientation, role):
        """
        Method to get header (index and columns) data
        """

        # Only horizontal
        if (orientation == QtCore.Qt.Vertical) and (role == QtCore.Qt.DisplayRole):
            return self.indexlabels[rowcol]

        elif (orientation == QtCore.Qt.Horizontal) and (role == QtCore.Qt.DisplayRole):
            return str(self.labels[rowcol])


class ExpertsListsModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with several lists related to the experts
    """

    def __init__(self, parentwidget):
        """
        Constructor

        Parameters
        ----------
        parentwidget : Table widget
            Widget of which this table model is part.
        """
        QtCore.QAbstractTableModel.__init__(self)

        self.parentwidget = parentwidget
        self.project = parentwidget.mainwindow.project
        self.mainwindow = parentwidget.mainwindow

        self.lists = [
            self.project.experts.ids,
            self.project.experts.names,
            self.project.experts.user_weights,
            self.project.experts.calibration,
            self.project.experts.info_real,
            self.project.experts.info_total,
            self.project.experts.weights,
        ]
        self.labels = ["ID", "Name", "User weight", "Calibration", "Info score real.", "Info score total", "Weight"]
        self.leftalign = []

        self.editable = [True, True, True, False, False, False, False]

    def flags(self, index):
        """
        Returns flags (properties) for a certain cell, based on the index

        Parameters
        ----------
        index : ModelIndex
            index of the cell

        Returns
        -------
        flags
            Properties of the cell
        """

        fl = QtCore.Qt.NoItemFlags

        if not index.isValid():
            return fl

        else:
            col = index.column()
            row = index.row()

            # Default flags
            fl |= Qt.Qt.ItemIsEnabled | Qt.Qt.ItemIsSelectable

            # Editable when assigned and not the normed weight column
            if col < len(self.lists) and self.editable[col]:
                fl |= Qt.Qt.ItemIsEditable

            # Checkable if actual expert
            if col == 0 and row in self.project.experts.actual_experts:
                fl |= QtCore.Qt.ItemIsUserCheckable

        return fl

    def columnCount(self, parent=None):
        """
        Also norm. weight columns are added for each DM,
        so the columnCount is larger than the default list model
        """
        return len(self.lists) + len(self.project.experts.decision_makers)

    def rowCount(self, parent=None):
        """
        Returns number of rows in table.
        """
        return len(self.lists[0])

    def headerData(self, rowcol, orientation, role):
        """
        Method to get header (index and columns) data
        """

        # Only horizontal
        if orientation == QtCore.Qt.Vertical:
            return None

        if role == QtCore.Qt.DisplayRole:
            if rowcol < len(self.lists):
                # Regular label
                return str(self.labels[rowcol])
            else:
                # Normalized weight label
                i = rowcol - len(self.lists)
                i = self.project.experts.decision_makers[i]
                return "Norm. W (" + self.project.experts.ids[i] + ")"

    def setData(self, index, value, role=Qt.Qt.EditRole):
        """
        Method to set data to cell. Changes the value in the list or array
        The value is checked for beigin in between other percentiles.
        """
        if not index.isValid():
            return False

        col = index.column()
        row = index.row()

        if role == QtCore.Qt.CheckStateRole and col == 0:
            self.layoutAboutToBeChanged.emit()
            self.parentwidget.toggle_expert(self.project.experts.ids[row])
            self.layoutChanged.emit()
            return True

        if self.labels[col] in ["ID", "Name"] and value == "":
            NotificationDialog(f"An empty expert ID or name is not allowed.")
            return False

        if self.labels[col] == "ID" and value in self.lists[col]:
            NotificationDialog(f"Expert ID is already present. Pick a unique ID.")
            return False

        # If empty value is given
        current = self.lists[col][row]
        if isinstance(current, float):
            self.lists[col][row] = np.nan if value == "" else float(value)
        else:
            self.lists[col][row] = value

        # Expert id changed, update the Id's in the other views and items
        if self.labels[col] == "ID":
            self.mainwindow.signals.update_ids()

        # Skip row after entering value
        self.parentwidget.table.setCurrentIndex(self.index(row + 1, col))

        # Unsaved changes
        self.mainwindow.setWindowModified(True)

        return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        Method to set the data to a cell. Sets value, alignment and color

        Parameters
        ----------
        index : int
            Index object with row and column
        role : Qt.DisplayRole, optional
            Property of data to display, by default QtCore.Qt.DisplayRole

        Returns
        -------
        QtCore.QVariant
            Property of data displayed
        """

        # Skip invalid
        if not index.isValid():
            return None

        # Check if excluded
        row, col = index.row(), index.column()
        excluded = self.project.experts.ids[row] in self.project.experts.excluded

        # Checkboxes for the actual experts
        if role == QtCore.Qt.CheckStateRole and col == 0:
            expert_id = self.project.experts.ids[row]
            if excluded:
                return QtCore.Qt.Unchecked
            elif row not in self.project.experts.actual_experts:
                return None
            else:
                return QtCore.Qt.Checked

        # Color when excluded
        elif role == QtCore.Qt.ForegroundRole and excluded:
            return QtGui.QBrush(QtCore.Qt.gray)

        # Alignment
        elif role == QtCore.Qt.TextAlignmentRole:
            if col in self.leftalign:
                return QtCore.QVariant(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            else:
                return QtCore.QVariant(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        # Get the data from the parent ListModel
        elif role == QtCore.Qt.DisplayRole:

            # Item from lists
            if col < len(self.lists):
                lst = self.lists[col]
                # if row < len(lst):
                # Get the item from the list
                item = lst[index.row()]
                return strformat(item)

            else:
                # Calculate normalized weight for expert
                weights = self.project.experts.weights
                # DM weight
                dm_idx = self.project.experts.decision_makers[col - len(self.lists)]
                # If the row indicates a decision maker, but not the one that matches the column, return None
                if (row in self.project.experts.decision_makers) and (row != dm_idx):
                    return None

                # Actual expert weight + dm weight
                tot_weight = weights[self.project.experts.get_idx("actual")].sum() + weights[dm_idx]

                return strformat(weights[row] / tot_weight)
