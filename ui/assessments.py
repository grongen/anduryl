from itertools import product

import numpy as np
from PyQt5 import Qt, QtCore, QtGui, QtWidgets

from anduryl import io
from anduryl.ui import widgets
from anduryl.ui.dialogs import NotificationDialog
from anduryl.ui.models import AssessmentArrayModel, ItemDelegate


class AssessmentsWidget(QtWidgets.QFrame):
    """
    Widget ot show the assessments. Consists of a table with
    all the values, and comboboxes to make a selection from the table.
    """

    def __init__(self, mainwindow):
        """
        Constructor
        
        Parameters
        ----------
        mainwindow : Main window class
            Main window of which the assessment widget is part.
        """

        super(AssessmentsWidget, self).__init__()

        self.mainwindow = mainwindow
        self.project = mainwindow.project
        self.init_ui()
    
    def init_ui(self):
        """
        Construct graphical interface
        """

        # Create the table view
        self.table = QtWidgets.QTableView()
        self.table.setStyleSheet("QTableView{border: 1px solid "+self.mainwindow.bordercolor+"}")
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.installEventFilter(self)
        
        # Create and add model
        self.model = AssessmentArrayModel(parentwidget=self)
        self.table.setModel(self.model)
        self.table.setItemDelegate(ItemDelegate(self.model))
        
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for i in range(2):
            self.table.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.Fixed)
            self.table.setColumnWidth(i, 100)
        
        # Buttonbox
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.setContentsMargins(2.5, 0, 2.5, 0)
        self.realization_label = QtWidgets.QLabel('')
        
        self.expert_cbox = QtWidgets.QComboBox()
        
        self.expert_cbox.setCurrentText('All experts')
        self.expert_cbox.currentIndexChanged.connect(self.set_expert)
        self.expert_cbox.setFixedWidth(95)
        
        self.item_cbox = QtWidgets.QComboBox()
        self.item_cbox.setCurrentText('All items')
        self.item_cbox.currentIndexChanged.connect(self.set_item)
        self.item_cbox.setFixedWidth(95)
        self.update_comboboxes()

        self.colorbutton = QtWidgets.QCheckBox()
        self.colorbutton.setChecked(False)
        self.colorbutton.clicked.connect(self.set_color)
        
        hlayout.addWidget(self.expert_cbox)
        hlayout.addWidget(self.item_cbox)
        hlayout.addWidget(self.realization_label)
        hlayout.addStretch()
        hlayout.addWidget(QtWidgets.QLabel('Colormap:'))
        hlayout.addWidget(self.colorbutton)

        self.label = QtWidgets.QLabel('Assessments')
        self.label.setContentsMargins(5, 2.5, 5, 2.5)
        self.label.setStyleSheet("QLabel {border: 1px solid "+self.mainwindow.bordercolor+"}")
        
        mainbox = widgets.VLayout([self.label, hlayout, self.table])
        
        self.setLayout(mainbox)

    def eventFilter(self, source, event):
        """
        Eventfilter for copying table content.
        """
        if (event.type() == QtCore.QEvent.KeyPress and
            event.matches(QtGui.QKeySequence.Copy)):
            selection = self.table.selectedIndexes()
            if selection:
                text = io.selection_to_text(selection)
                QtWidgets.qApp.clipboard().setText(text)
                return True
        return self.mainwindow.eventFilter(source, event)

    def to_csv(self):
        io.table_to_csv(self.model, self.mainwindow)

    def change_quantiles(self, *args, newquantiles=None):
        """
        Method to call when the project quantiles are changes.

        Opens a dialog to set the quantiles, if they are not given as keyword argument.
        Adds or removes quantiles from the assessments untill the
        project matches the given quantiles.
        
        Parameters
        ----------
        newquantiles : list, optional
            Quantiles, if given no window is opened, by default None
        """
        
        if newquantiles is None:
            self.parameters_dialog = QuantileDialog(self)
            self.parameters_dialog.exec_()

            if self.parameters_dialog.succeeded:
                # Get items
                items = [self.parameters_dialog.table.item(i, 0) for i in range(self.parameters_dialog.table.rowCount())]
                newquantiles = [float(item.data(0)) for item in items if (item is not None and item.data(0) != '')]
            else:
                newquantiles = None

        if newquantiles is not None:
            # Add new quantiles
            for quantile in newquantiles:
                if quantile not in self.project.assessments.quantiles:
                    self.project.assessments.add_quantile(quantile)

            # Remove old quantiles
            for i in reversed(range(len(self.project.assessments.quantiles))):
                quantile = self.project.assessments.quantiles[i]
                if quantile not in newquantiles:
                    self.project.assessments.remove_quantile(quantile)
                    
            self.mainwindow.signals.update_gui()
            self.mainwindow.signals.update_headers()
        
    def set_color(self):
        """
        Toggle background colors for assessments table.
        """
        on = self.colorbutton.isChecked()
        self.model.layoutAboutToBeChanged.emit()
        self.model.colored = on
        self.table.setShowGrid(on)
        self.table.setAlternatingRowColors(not on)
        self.model.layoutChanged.emit()

    def set_expert(self):
        """
        Method called when expert combobox changed.
        Updates the selection of the array to show.
        """
        expert = self.expert_cbox.currentText()
        self.model.layoutAboutToBeChanged.emit()
        if expert == 'All experts':
            # Show the complete array
            self.model.selector.update()
        else:
            self.item_cbox.setCurrentText('All items')
            # Only show the selected expert in the array (but all items)
            idx = self.project.experts.ids.index(expert)
            self.model.selector.update(dim=0, index=idx)
        self.model.layoutChanged.emit()
        
    def set_item(self):
        """
        Method called when item combobox changed.
        Updates the selection of the array to show.
        """
        item = self.item_cbox.currentText()
        self.model.layoutAboutToBeChanged.emit()
        if item == 'All items':
            # Show the complete array
            self.model.selector.update()
        else:
            self.expert_cbox.setCurrentText('All experts')
            idx = self.project.items.ids.index(item)
            # Only show the selected item in the array (but all experts)
            self.model.selector.update(dim=2, index=idx)
        self.model.layoutChanged.emit()

        self.update_label()

    def update_label(self):
        """
        Method to update the label that is shown next to the item selection.
        It the item is a realization (has a known answer) the answer is shown.
        Otherwise the shows value is an empty string.
        """

        # Get item
        item = self.item_cbox.currentText()
        if item == 'All items':
            self.realization_label.setText(f'')
            return None

        # Set realization as label
        idx = self.project.items.ids.index(item)
        value = self.project.items.realizations[idx]
        if not np.isnan(value):
            self.realization_label.setText(f'Realization: {value:.4g}')
        else:
            self.realization_label.setText(f'')
            
    def update_comboboxes(self):
        """
        Update the comboboxes. This method is called when the items in the
        comboboxes need to be changed. It matches these items (or experts)
        with the items or experts in the project. If the currently selected
        item is removed, the combobox changes to "All items" or "All experts"
        """

        # Add or remove experts
        for name in ['expert', 'item']:
            cbox = getattr(self, name+'_cbox')
            ids = getattr(self.project, name+'s').ids

            # Get items
            current_item = cbox.currentText()
            cbox_items = [cbox.itemText(i) for i in range(cbox.count())]
            project_items = ids + [f'All {name}s']

            # Add items that are not already present
            for item in project_items:
                if item not in cbox_items:
                    cbox.addItem(item)

            # Remove items that where removed from the project
            for i, item in enumerate(cbox_items):
                if item not in project_items:
                    cbox.removeItem(i)
                
                    # If the current item is removed, reset to 'All items'
                    if item == current_item:
                        cbox.setCurrentText(f'All {name}s')

    def change_combobox_ids(self):
        """
        Method called when an item name has changed. Looks for items
        that do not match, removes the item at that position and
        replaces it with the new item.
        """
        # Add or remove experts
        for name in ['expert', 'item']:
            cbox = getattr(self, name+'_cbox')
            ids = getattr(self.project, name+'s').ids

            # Get items
            cbox_items = [cbox.itemText(i) for i in range(cbox.count())]
            project_items = ids + [f'All {name}s']

            # Rename item
            for proj_item in project_items:
                if proj_item not in cbox_items:
                    break

            for i, cb_item in enumerate(cbox_items):
                # If changed item is found
                if cb_item not in project_items:
                    cbox.removeItem(i)
                    cbox.insertItem(i, proj_item)
                    
                
class QuantileDialog(QtWidgets.QDialog):
    """
    Dialog to get parameters for calculating decision maker
    """

    def __init__(self, assessmentswidget):
        """
        Constructor
        """
        self.assessmentswidget = assessmentswidget
        self.assessments = assessmentswidget.project.assessments
        super(QuantileDialog, self).__init__()

        self.succeeded = False
        self._init_ui()
        
    def _init_ui(self):
        """
        Set up UI design
        """

        self.setWindowTitle('Quantiles')
        self.table = QtWidgets.QTableWidget()
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.table.setRowCount(len(self.assessments.quantiles)+1)
        self.table.setColumnCount(1)
        self.table.horizontalHeader().setStretchLastSection(True)
        for i, quantile in enumerate(self.assessments.quantiles):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(f'{quantile:.4g}'))
        self.table.itemChanged.connect(self.update_items)
        
        # OK and Cancel buttons
        self.generate_button = QtWidgets.QPushButton('Accept')
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self.accept)

        self.cancel_button = QtWidgets.QPushButton('Cancel')
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.close)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.generate_button, QtWidgets.QDialogButtonBox.ActionRole)
        button_box.addButton(self.cancel_button, QtWidgets.QDialogButtonBox.RejectRole)

        # button_box.accepted.connect(QtWidgets.QDialog.accept)

        self.label = QtWidgets.QLabel('Edit quantiles by adding or erasing items:')

        self.setLayout(widgets.VLayout([self.label, self.table, widgets.HLine(), button_box]))

    def accept(self):
        """
        Sets succeeded attribute to True and calls the close function.
        """
        self.succeeded = True
        self.close()

    def update_items(self):
        """
        Update function that updates the items after one has been added or removed.
        The items are retrieved, sorted and assigned to the table.
        """
        # Get items
        items = [self.table.item(i, 0) for i in range(self.table.rowCount())]
        # Sort
        tablevalues = sorted(set([float(item.data(0)) for item in items if (item is not None and item.data(0) != '')]))
        # Check values
        for i in reversed(range(len(tablevalues))):
            if not 0.0 < tablevalues[i] < 1.0:
                NotificationDialog('Quantiles should be > 0.0 and < 1.0')
                del tablevalues[i]

        self.table.itemChanged.disconnect()
        self.table.setRowCount(len(tablevalues)+1)
        for i, quantile in enumerate(tablevalues):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(f'{quantile:.4g}'))
        self.table.setItem(len(tablevalues), 0, QtWidgets.QTableWidgetItem(''))
        self.table.itemChanged.connect(self.update_items)
