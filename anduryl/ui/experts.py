from itertools import product

import numpy as np
from anduryl import io
from anduryl.io.settings import CalculationSettings, CalibrationMethod, Distribution, WeightType
from anduryl.ui import menus, widgets
from anduryl.ui.dialogs import NotificationDialog
from anduryl.ui.models import ExpertsListsModel, ItemDelegate
from PyQt5 import QtCore, QtGui, QtWidgets


class ExpertsWidget(QtWidgets.QFrame):
    """
    Widget with the expert table
    """

    def __init__(self, mainwindow):
        """
        Constructor
        """
        super(ExpertsWidget, self).__init__()

        self.mainwindow = mainwindow
        self.project = mainwindow.project
        self.construct_widget()

        self.calc_settings = CalculationSettings(
            id="DM",
            name="Decision Maker",
            weight=WeightType.GLOBAL,
            overshoot=0.1,
            alpha=0.0,
            optimisation=True,
            robustness=True,
            calpower=1.0,
        )

        # Create combinations of color and linestyle for cycling through
        colors = [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
        ]
        linestyles = ["-", "--", ":", "-."]
        self.styles = list(product([colors, linestyles]))

    def construct_widget(self):
        """
        Constructs the widget
        """
        # Create the table view
        # TODO: Add number of answered questions to table
        self.table = QtWidgets.QTableView()
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableView{border: 1px solid " + self.mainwindow.bordercolor + "}")
        self.table.installEventFilter(self)

        # Create and add model
        self.model = ExpertsListsModel(parentwidget=self)
        self.table.setModel(self.model)
        self.table.setItemDelegate(ItemDelegate(self.model))

        for i in range(self.model.columnCount()):
            self.table.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)

        mainbox = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Experts")
        label.setContentsMargins(5, 3, 5, 3)
        label.setStyleSheet("QLabel {border: 1px solid " + self.mainwindow.bordercolor + "}")

        mainbox.addWidget(label)
        mainbox.addWidget(self.table)

        self.setLayout(mainbox)

    def eventFilter(self, source, event):
        """
        Eventfilter for copying table content.
        """
        if event.type() == QtCore.QEvent.KeyPress and event.matches(QtGui.QKeySequence.Copy):
            selection = source.selectedIndexes()
            if selection:
                text = io.table.selection_to_text(selection)
                QtWidgets.qApp.clipboard().setText(text)
                return True
        return self.mainwindow.eventFilter(source, event)

    def to_csv(self):
        """
        Calls the anduryl.io.table_to_csv function for the table model
        """
        io.table_to_csv(self.model, self.mainwindow)

    def add_decision_maker(self):
        """
        Function called when a user clicks 'calculate'

        First the presence of experts and items are checked. If one of them is
        not present, send a notification to the user.

        After that a window with calculation options is opened. If accepted (OK)
        a decision maker is calculated with the given options. If robustness
        is checked, also the robustness tables for 1 expert and 1 item are
        calculated.
        """

        # Check if there are any experts
        if len(self.project.experts.actual_experts) == 0:
            NotificationDialog("Add at least one expert before calculating a decision maker.")
            return None

        # Check if there are any items
        if len(self.project.items.ids) == 0:
            NotificationDialog("Add at least one item before calculating a decision maker.")
            return None

        # Launch window for settings
        self.parameters_dialog = DecisionMakerOptions(self)
        self.parameters_dialog.exec_()
        if not self.parameters_dialog.succeeded:
            return None

        # If user weights, check weights.
        if self.calc_settings.weight == WeightType.USER:
            expert_user_weight, message = self.project.experts.check_user_weights()
            if message:
                NotificationDialog(message)
            if expert_user_weight is None:
                return None

        self.mainwindow.setCursorWait()

        # Calculate decision maker
        self.mainwindow.signals.layout_about_to_be_changed.emit()

        # Add results to project from settings. These are frozen results.
        success = self.project.add_results_from_settings(self.calc_settings)
        self.mainwindow.signals.layout_changed.emit()

        # Add calculated results to GUI
        if success:
            self.mainwindow.resultswidget.add_results(resultid=self.calc_settings.id)

        # Update GUI
        self.mainwindow.signals.update_gui.emit()

        # Move splitter if results are hidden
        if self.mainwindow.rightsplitter.sizes()[-1] == 0 and success:
            self.mainwindow.rightsplitter.setSizes([200, 400])

        self.mainwindow.setCursorNormal()

    def add_expert(self):
        """
        Add a new expert to the project. Adds a row to the experts table
        """
        # Define name and id
        nth_expert = len(self.project.experts.ids) + 1
        default_id = f"Exp{nth_expert:02d}"
        default_name = f"Expert {nth_expert:02d}"

        # Add expert
        self.project.experts.add_expert(
            exp_id=default_id, exp_name=default_name, assessment=None, exp_type="actual", overwrite=False
        )

        # Update GUI
        self.mainwindow.signals.update_gui.emit()
        self.mainwindow.signals.update_color_range.emit()
        self.mainwindow.signals.set_window_modified.emit(True)

    def remove_expert_clicked(self):
        """
        Method executed when the action remove expert is clicked.
        """
        rownum = self.table.currentIndex().row()
        if rownum == -1:
            NotificationDialog("Select a row to remove an expert")
            return None

        expertid = self.project.experts.ids[rownum]

        # If decision maker, also close the results tab
        if rownum in self.project.experts.decision_makers:
            self.mainwindow.resultswidget.close_results(index=None, expert=expertid)

        # Remove expert from table widget
        self.remove_expert(expertid)

    def remove_expert(self, expertid):
        """
        Removes the expert from the project, by expert id

        Parameters
        ----------
        expertid : str, optional
            Expert ID
        """
        # Get index
        expnum = self.project.experts.get_idx(expertid)

        if expnum in self.project.experts.actual_experts:
            self.mainwindow.signals.set_window_modified.emit(True)

        # Remove expert from project
        self.project.experts.remove_expert(expertid)

        # Update UI
        self.mainwindow.assessmentswidget.table.setCurrentIndex(QtCore.QModelIndex())
        self.mainwindow.signals.update_gui.emit()
        self.mainwindow.signals.update_color_range.emit()
        self.table.setCurrentIndex(QtCore.QModelIndex())

    def exclude_expert_clicked(self):
        """
        Executed when expert checkbox is clicked
        """
        rownum = self.table.currentIndex().row()
        if rownum == -1:
            NotificationDialog("Select a row to exclude an expert")
            return None

        # Remove expert from table widget
        self.toggle_expert(self.project.experts.ids[rownum])

    def toggle_expert(self, expert):
        """
        Toggle and expert on or off. The expert is added or removed
        to or from the excluded list

        Parameters
        ----------
        expert : str, optional
            Expert ID
        """
        if expert in self.project.experts.excluded:
            self.project.experts.excluded.remove(expert)
        else:
            self.project.experts.excluded.append(expert)

    def contextMenuEvent(self, event):
        """
        Creates the context menu for the expert widget
        """

        menu = menus.ExpertsContextMenu(self, event)


class DecisionMakerOptions(QtWidgets.QDialog):
    """
    Dialog to get parameters for calculating decision maker
    """

    def __init__(self, expertwidget=None):
        """
        Constructor
        """
        super(DecisionMakerOptions, self).__init__(expertwidget)

        # Flags for updating names
        self.auto_update_id = True
        self.auto_update_name = True

        # Get all settings
        self.expertwidget = expertwidget
        self.calc_settings = self.expertwidget.calc_settings
        if self.calc_settings.alpha is None:
            self.calc_settings.alpha = 0.0

        self.setWindowTitle("Anduryl - Calculation settings")
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        # Built UI
        self.input_elements = {}
        self._init_ui()
        self.load_from_settings()

        self.update_name_id()

        self.valid = False
        self.succeeded = False

    def _init_ui(self):
        """
        Set up UI design
        """
        # Create GUI elements, set them in dict structure
        alpha_symbol = "\u03B1"
        labelwidth = widgets.get_width(f"Calibration cut-off ({alpha_symbol}):")

        self.input_elements["weight"] = widgets.ComboboxInputLine(
            label="Weights:",
            labelwidth=labelwidth,
            items=[
                WeightType.GLOBAL.value,
                WeightType.ITEM.value,
                WeightType.EQUAL.value,
                WeightType.USER.value,
            ],
        )
        self.input_elements["optimisation"] = widgets.CheckBoxInput(
            label="DM optimisation:", labelwidth=labelwidth
        )
        self.input_elements["robustness"] = widgets.CheckBoxInput(label="Robustness:", labelwidth=labelwidth)
        self.input_elements["overshoot"] = widgets.ParameterInputLine(
            label="Intrinsic range:", labelwidth=labelwidth, validator=QtGui.QDoubleValidator(0.01, 100.0, 4)
        )
        self.input_elements["alpha"] = widgets.ParameterInputLine(
            label=f"Calibration cut-off ({alpha_symbol}):",
            labelwidth=labelwidth,
            validator=QtGui.QDoubleValidator(0.00, np.inf, 4),
        )
        self.input_elements["calpower"] = widgets.ParameterInputLine(
            label=f"Calibration power:",
            labelwidth=labelwidth,
            validator=QtGui.QDoubleValidator(1e-6, np.inf, 4),
        )
        self.input_elements["id"] = widgets.ParameterInputLine(label="ID:", labelwidth=labelwidth)
        self.input_elements["name"] = widgets.ParameterInputLine(label="Name:", labelwidth=labelwidth)
        self.input_elements["distribution"] = widgets.ComboboxInputLine(
            label="Distribution:",
            labelwidth=labelwidth,
            items=[Distribution.PWL.value, Distribution.METALOG.value],
        )

        self.input_elements["calibration_method"] = widgets.ComboboxInputLine(
            label="Calibration method:",
            labelwidth=labelwidth,
            items=[item.value for item in CalibrationMethod.__members__.values()],
        )

        # Connect signals
        self.input_elements["id"].LineEdit.editingFinished.connect(self.disable_update_id)
        self.input_elements["name"].LineEdit.editingFinished.connect(self.disable_update_name)
        self.input_elements["weight"].combobox.currentIndexChanged.connect(self.update_name_id)
        self.input_elements["optimisation"].checkbox.stateChanged.connect(self.update_name_id)
        self.input_elements["optimisation"].checkbox.stateChanged.connect(self.toggle_visibility)
        self.input_elements["weight"].combobox.currentIndexChanged.connect(self.toggle_visibility)

        # Create base layout
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(10)

        for key, item in self.input_elements.items():
            self.layout().addWidget(item)

        self.layout().addWidget(widgets.HLine())

        # OK and Cancel buttons
        self.generate_button = QtWidgets.QPushButton("Calculate")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self.calculate_dm)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.cancel)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.generate_button, QtWidgets.QDialogButtonBox.ActionRole)
        button_box.addButton(self.cancel_button, QtWidgets.QDialogButtonBox.RejectRole)

        button_box.accepted.connect(QtWidgets.QDialog.accept)
        # button_box.rejected.connect(QtWidgets.QDialog.reject)

        self.layout().addWidget(button_box)

    def disable_update_id(self):
        """
        Disables to auto updating of the id. Is called after the user
        changes the id manually.
        """
        self.auto_update_id = False

    def disable_update_name(self):
        """
        Disables to auto updating of the name. Is called after the user
        changes the name manually.
        """
        self.auto_update_name = False

    def update_name_id(self):
        """
        Method to update the id and name when the settings change
        """
        if self.auto_update_id:
            idtext = self.input_elements["weight"].combobox.currentText()[:2].upper()
            if idtext.lower() in ["gl", "it"] and self.input_elements["optimisation"].checkbox.isChecked():
                idtext += "opt"

            if idtext in self.expertwidget.project.experts.ids:
                for i in range(2, 99):
                    if idtext + " " + str(i) not in self.expertwidget.project.experts.ids:
                        break
                idtext += " " + str(i)

            self.input_elements["id"].LineEdit.setText(idtext)

        if self.auto_update_name:
            name = self.input_elements["weight"].combobox.currentText()
            if name in [WeightType.GLOBAL, WeightType.ITEM]:
                if self.input_elements["optimisation"].checkbox.isChecked():
                    name += " Opt."
                else:
                    name += " No opt."

            if name in self.expertwidget.project.experts.names:
                for i in range(2, 99):
                    if name + " " + str(i) not in self.expertwidget.project.experts.names:
                        break
                name += " " + str(i)

            self.input_elements["name"].LineEdit.setText(name)

    def toggle_visibility(self):
        """
        Updates the visibility (enables or greyed out) of all options in the
        menu after the options have changed.
        """
        optimisation = self.input_elements["optimisation"].checkbox.isChecked()
        weight = self.input_elements["weight"].combobox.currentText()

        if weight not in [WeightType.GLOBAL.value, WeightType.ITEM.value]:
            self.input_elements["optimisation"].checkbox.setChecked(False)
            self.input_elements["optimisation"].checkbox.setEnabled(False)
            self.input_elements["robustness"].checkbox.setChecked(False)
            self.input_elements["robustness"].checkbox.setEnabled(False)
        else:
            self.input_elements["optimisation"].checkbox.setEnabled(True)
            self.input_elements["robustness"].checkbox.setEnabled(True)

        # Visible if no optimisation and global or item weight
        visible = (not optimisation) and (weight in [WeightType.GLOBAL.value, WeightType.ITEM.value])
        self.input_elements["alpha"].LineEdit.setEnabled(visible)

    def calculate_dm(self):
        """
        User pressed Generate button
        """
        # Validate the input
        self.validate()

        # Return none if validation failed
        if not self.valid:
            return None

        # Save to settings
        self.save_to_settings()

        # Check if expert id is new
        exp_id = self.calc_settings.id
        if exp_id in self.expertwidget.project.experts.ids:
            NotificationDialog(f'Expert ID "{exp_id}" is already in use. Pick an unused ID.')
            return None

        # Set project dirty
        # self.mainwindow.setDirty()

        # Set project succeeded
        self.succeeded = True
        self.accept()

    def cancel(self):
        """
        User pressed Cancel button
        """
        self.succeeded = False
        self.reject()

    def is_not_empty(self, val):
        """
        Validate parameter based on 3 conditions:
        1. is not nan
        2. is not None
        3. is not ''
        """
        valid = True
        # Lists are not checked
        if isinstance(val, list):
            return valid

        # Check for NaN's
        if isinstance(val, (float, np.float)):
            if np.isnan(val):
                valid = False

        # Check for None or empty
        if (val is None) or (val == ""):
            valid = False

        return valid

    def validate(self, check_empty=True):
        """
        Test for correct input in this dialog

        Parameters
        ----------
        check_empty : boolean
            Whether to check the empty parameters. This is not done when the table
            is loaded from settings, since it then does not matter if there
            are empty cells.
        """

        # Collect invalid parameters
        invalid = []
        parameters = []

        # Loop trough input elements and validate
        for widget in self.input_elements.values():
            val = widget.get_value()
            # If not checking the empty parameters, if a parameter is empty, continue
            if not check_empty:
                if not self.is_not_empty(val):
                    continue

            # Check if item is filled
            if not self.is_not_empty(val):
                invalid.append(widget.label.replace(":", ""))
                parameters.append(val)

            # If the item has a validator, check if the value is valid
            elif hasattr(widget, "validator"):
                if widget.validator is not None:
                    if widget.validator.validate(val, 1)[0] != 2:
                        invalid.append(widget.label.replace(":", ""))
                        parameters.append(val)

        if len(invalid) == 1:
            NotificationDialog('No valid value was entered for "{}": {}'.format(invalid[0], parameters))
            self.valid = False

        elif len(invalid) > 1:
            NotificationDialog(
                'No valid values were entered for "{}": {}'.format('", "'.join(invalid), parameters)
            )
            self.valid = False

        else:
            # If no error
            self.valid = True

    def save_to_settings(self):
        """
        Save parameters to settings. The settings have the same layout as the input_elements dict
        """
        for param, widget in self.input_elements.items():
            val = widget.get_value()
            # Convert value to integer of float
            try:
                val = float(val)
                if val.is_integer():
                    val = int(val)
            except:
                pass
            setattr(self.calc_settings, param, val)

    def load_from_settings(self):
        """
        Save parameters to settings. The settings have the same layout as the input_elements dict
        """
        for param, value in self.calc_settings._iter():

            # Check if parameter is not empty before filling in
            if self.is_not_empty(value):
                self.input_elements[param].set_value(value)
        # Validate
        self.validate(check_empty=False)
