import json
import textwrap
from math import factorial
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from anduryl import io
from anduryl.io.settings import SaveFigureSettings
from anduryl.model.results import PlotData
from anduryl.ui import menus, widgets
from anduryl.ui.models import ArrayModel, ListsModel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from PyQt5 import Qt, QtCore, QtGui, QtWidgets

plt.rcParams["axes.linewidth"] = 0.5
plt.rcParams["axes.labelsize"] = 9
plt.rcParams["axes.titlesize"] = 9
plt.rcParams["xtick.labelsize"] = 9
plt.rcParams["ytick.labelsize"] = 9
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["legend.handletextpad"] = 0.4
plt.rcParams["legend.fontsize"] = 8
plt.rcParams["legend.labelspacing"] = 0.2
plt.rcParams["legend.fancybox"] = False

plt.rcParams["font.size"] = 9

plt.rcParams["lines.linewidth"] = 1.5  # line width in points
plt.rcParams["lines.markeredgewidth"] = 0
plt.rcParams["lines.markersize"] = 5

# plt.rcParams["figure.dpi"] = 50


def get_markers(quantiles: list):
    # Define markerset to choose from. From closest to 0.5 to furthest away from 0.5
    markerset = ["d", "o", "X", "^", "s", "h", "*", "2"]
    # Determine the position from 0.5. Equal far away (i.e., 0.05 and 0.95 or 0.25 and 0.75) are assigned the same marker
    _, inv = np.unique(np.abs(np.array(quantiles) - 0.5).astype(np.float32), return_inverse=True)
    # Create the markerset
    markers = [markerset[i] for i in inv]
    return markers


class ResultsWidget(QtWidgets.QFrame):
    """
    Widget that contains all resultoverview in seperate tabs.
    """

    def __init__(self, mainwindow):
        """
        Constructor

        Parameters
        ----------
        mainwindow : mainwindow class
            Main project widget
        """

        super(ResultsWidget, self).__init__()

        self.mainwindow = mainwindow
        self.project = mainwindow.project

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_results)

        self.dm_ids = []

        label = QtWidgets.QLabel("Results")
        label.setContentsMargins(5, 3, 5, 3)
        label.setStyleSheet("QLabel {border: 1px solid " + self.mainwindow.bordercolor + "}")

        self.setLayout(widgets.VLayout([label, self.tabs]))

    def add_results(self, resultid):
        """
        Add results in an Resultsoverview to the tabs. The specific
        results are derived from the settings, and passed to the
        overview

        Parameters
        ----------
        settings : dictionary
            Calculation setting
        """

        # Get results to create overview
        results = self.project.results[resultid]
        resultsoverview = ResultOverview(self, results)

        # Add to tabs
        self.tabs.addTab(resultsoverview, resultid + " (" + results.settings.name + ")")
        self.dm_ids.append(resultid)

        # Add to export menu
        self.mainwindow.add_export_actions(resultsoverview)

    def get_results(self, index=None, expert=None):
        # When the function is called by expert id, find the index
        if expert is not None:
            index = self.dm_ids.index(expert)
        # Get current widget
        currentQWidget = self.tabs.widget(index)
        # Get results
        return currentQWidget.results

    def close_results(self, index=None, expert=None):
        """
        Removes results from the widget. Results can be removed
        by index or by expert id. If the results are removed by
        index, the results are also removed from the expert widget.
        The function is thus used in slightly different ways.

        Parameters
        ----------
        index : int, optional
            Index of results to remove, by default None
        expert : str, optional
            Id of expert (decision maker) to remove, by default None
        """

        # When the function is called by expert id, find the index
        if expert is not None:
            index = self.dm_ids.index(expert)

        # Get current widget
        currentQWidget = self.tabs.widget(index)
        # Delete widget
        currentQWidget.deleteLater()
        # Close tab
        self.tabs.removeTab(index)
        currentQWidget.close()

        # Delete DM
        dm_id = self.dm_ids[index]
        del self.dm_ids[index]

        # If the function is called by index, and thus expert is None, remove also from table
        # If called by expert, the call comes from the table widget, and so removing is not needed
        if expert is None:
            # Remove from experts
            self.mainwindow.expertswidget.remove_expert(dm_id)

        # Remove from export menu
        self.mainwindow.remove_export_actions(dm_id)

        # Collapse results if last is removed
        if len(self.dm_ids) == 0:
            self.mainwindow.rightsplitter.setSizes([1, 0])


class ResultOverview(QtWidgets.QScrollArea):
    """
    Widget with results for a decision maker.
    """

    def __init__(self, resultswidget, results):
        """
        Copy results from current project. Note that the results are copied
        and not refered to, since we want to 'freeze' the current project in
        these results.
        """

        super(ResultOverview, self).__init__()

        self.resultswidget = resultswidget
        self.mainwindow = resultswidget.mainwindow

        # TODO Copy results and settings
        self.results = results
        self.settings = self.results.settings

        # Calculate lower bounds once. Since these results are frozen the bounds won't change
        self.results.lower_k, self.results.upper_k = self.results.assessments.get_bounds(
            overshoot=self.settings.overshoot
        )
        self.results.lower, self.results.upper = self.results.assessments.get_bounds()

        self.robustness_model = {}
        self.init_ui()

    def init_ui(self):
        """
        Set up the result overview in the user interface.
        """

        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.setWidgetResizable(True)
        layout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addLayout(layout)
        hlayout.addStretch()
        widget = QtWidgets.QWidget()
        widget.setLayout(hlayout)
        self.setWidget(widget)

        label_layout = QtWidgets.QGridLayout()
        label_layout.setHorizontalSpacing(20)

        # Add results settings
        label_layout.addWidget(QtWidgets.QLabel(f"Weights: {self.settings.weight.value}"), 0, 0)
        label_layout.addWidget(QtWidgets.QLabel(f"SA method: {self.settings.calibration_method.value}"), 1, 0)
        
        label_layout.addWidget(
            QtWidgets.QLabel(f"Optimisation: {'yes' if self.settings.optimisation else 'no'}"), 1, 1
        )
        label_layout.addWidget(QtWidgets.QLabel(f"Intrinsic range: {self.settings.overshoot}"), 0, 2)
        label_layout.addWidget(QtWidgets.QLabel(f"Significance level: {self.results.alpha_opt:.4g}"), 0, 1)
        label_layout.addWidget(QtWidgets.QLabel(f"Calibration power: {self.settings.calpower}"), 1, 2)

        label_layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum), 0, 3)
        

        self.plot_items_button = QtWidgets.QPushButton("Plot results", clicked=self.plot_items)
        self.plot_items_button.setFixedWidth(100)

        layout.addWidget(
            widgets.SimpleGroupBox(
                [label_layout, self.plot_items_button], "vertical", "Decision maker characteristics"
            )
        )

        # Add table with expert results (weights etcetera)
        table = self.add_expert_weights_table()

        self.show_item_weights_button = QtWidgets.QPushButton("Info score per item", clicked=self.show_items)
        self.show_item_weights_button.setFixedWidth(100)

        layout.addWidget(
            widgets.SimpleGroupBox(
                [table, self.show_item_weights_button], "vertical", "Expert and DM weights"
            )
        )

        # Add a table for the item robustness
        if self.results.item_robustness or self.results.expert_robustness:
            self.robustness_tables = QtWidgets.QTabWidget()

            if self.results.item_robustness:
                seedidx = self.results.items.get_idx("seed")
                seeditems = [None] + [item for i, item in enumerate(self.results.items.ids) if seedidx[i]]
                item_array = np.vstack(
                    [
                        self.results.item_robustness[tuple([itemid] if itemid is not None else [])]
                        for itemid in seeditems
                    ]
                )
                seeditems[0] = "None"

                self.ui_add_robustness_table("Items", seeditems, item_array)

            if self.results.expert_robustness:
                experts = [None] + self.results.experts.get_exp("actual")
                expert_array = np.vstack(
                    [
                        self.results.expert_robustness[tuple([exp] if exp is not None else [])]
                        for exp in experts
                    ]
                )
                experts[0] = "None"

                self.ui_add_robustness_table("Experts", experts, expert_array)

            # Plot layout
            self.plot_excluded_button = QtWidgets.QPushButton(
                "Plot multiple exluded items", clicked=self.plot_excluded_items
            )
            button_layout = widgets.HLayout([self.plot_excluded_button])
            button_layout.addStretch()
            layout.addWidget(
                widgets.SimpleGroupBox([self.robustness_tables, button_layout], "vertical", "Robustness")
            )

        layout.addStretch()

    def add_expert_weights_table(self):
        # Create the table view
        table = QtWidgets.QTableView()
        self.scores_table = table
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)

        # Create and add model
        self.scores_model = ListsModel(
            lists=[
                self.results.experts.ids,
                self.results.experts.names,
                self.results.experts.calibration,
                self.results.experts.info_real,
                self.results.experts.info_total,
                self.results.experts.comb_score,
                self.results.experts.weights,
            ],
            labels=[
                "ID",
                "Name",
                "Calibration",
                "Info score real.",
                "Info score total",
                "Comb score",
                "Weight",
            ],
        )
        table.setModel(self.scores_model)

        width, height = widgets.get_table_size(table, self.scores_model)
        table.setMinimumHeight(height)
        table.setMaximumHeight(height)
        table.setMinimumWidth(width)
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Copy event
        table.installEventFilter(self)

        return table

    def ui_add_robustness_table(self, key, index, array):
        """
        Adds a robustness table (experts or items) to the UI

        Parameters
        ----------
        key : str
            Experts or Items
        index : list
            Index for each table row
        array : np.ndarray
            Numpy arra with values to show in table
        """
        table = QtWidgets.QTableView()
        table.verticalHeader().setVisible(True)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)

        self.robustness_model[key] = ArrayModel(
            array=array,
            labels=[index, ["Info score total", "Info score real.", "Calibration"]],
            coldim=1,
            rowdim=[0],
            index_names=["Item ID"],
            index=True,
        )

        table.setModel(self.robustness_model[key])
        table.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.robustness_tables.addTab(table, key)
        width, height = widgets.get_table_size(table, self.robustness_model[key])
        table.setMinimumHeight(height)
        table.setMaximumHeight(height)
        table.setMinimumWidth(width)
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        table.installEventFilter(self)

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

    def plot_excluded_items(self):
        """
        Opens a dialog to plot robustness for excluding multiple items.
        """
        self.plot_dialog = PlotExcludedDialog(self)
        self.plot_dialog.exec_()

    def show_items(self):
        """
        Opens a dialog to information scores per item.
        """
        self.parameters_dialog = ItemWeightDialog(self)
        self.parameters_dialog.exec_()

    def plot_items(self):
        """
        Opens a dialog to plot the distributions for experts and decision makers.
        """
        self.plot_dialog = PlotDistributionsDialog(self)
        self.plot_dialog.exec_()


class LegendTable(QtWidgets.QTableWidget):
    """
    This widget is the table besides the distributions plot.
    It functions as an interactive legend, in which different
    lines can be toggled on and of.
    """

    def __init__(self, dialog):
        """
        Constructor

        Parameters
        ----------
        dialog : PlotDistributionsDialog
            The parent dialog window in which the distributions are plotted.
        """

        self.dialog = dialog
        self.results = dialog.results
        self.colors = dialog.colors

        # Create a collection of weights. Since extra experts can be added,
        # we define this seperately
        self.comb_score_collection = list(self.results.experts.comb_score)

        # Add a list for storing the labels
        self.labels = []

        super(QtWidgets.QTableWidget, self).__init__()

        self.construct_widget()

    def construct_widget(self):
        """
        Constructs the widget.
        """
        # Create legend table
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setMinimumSectionSize(12)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        self.setColumnCount(3)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.horizontalHeader().setHighlightSections(False)
        self.setHorizontalHeaderLabels(["", "Expert", "Weight"])
        self.setColumnWidth(0, 10)

        self.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.setSelectionMode(QtWidgets.QTableWidget.MultiSelection)

        p = QtGui.QPalette()
        # Both active and inactive should follow inactive layout
        for group in [QtGui.QPalette.Active, QtGui.QPalette.Inactive]:
            # Switch background
            p.setColor(
                group, QtGui.QPalette.Highlight, p.color(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight)
            )
            # p.setColor(group, QtGui.QPalette.Base, p.color(QtGui.QPalette.Inactive, QtGui.QPalette.Base))

            # Set text colors
            p.setColor(
                group,
                QtGui.QPalette.HighlightedText,
                p.color(QtGui.QPalette.Inactive, QtGui.QPalette.HighlightedText),
            )
            p.setColor(group, QtGui.QPalette.Text, p.color(QtGui.QPalette.Inactive, QtGui.QPalette.Dark))
        self.setPalette(p)

        self.itemSelectionChanged.connect(self.dialog._set_data_visible)
        self.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

    def set_rows(self):
        """
        Fill in the legend with all the expert id's and weights
        """

        plotby = self.dialog.plotby_cbox.combobox.currentText().lower()
        if plotby == "expert":
            self.labels = self.results.items.ids
            self.setHorizontalHeaderLabels(["", "Item", ""])
        elif plotby == "item":
            self.labels = self.results.experts.ids
            self.setHorizontalHeaderLabels(["", "Expert", "Weight"])
        else:
            raise KeyError(plotby)

        nrows = len(self.labels)

        self.setFixedHeight(min(24 * (nrows + 1), 400))

        self.itemSelectionChanged.disconnect()

        self.setRowCount(nrows)

        for i in range(nrows):
            self.setItem(i, 1, QtWidgets.QTableWidgetItem(self.labels[i]))
            if plotby == "item":
                self.setItem(i, 2, QtWidgets.QTableWidgetItem(f"{self.comb_score_collection[i]:.4g}"))
            if plotby == "expert":
                self.setItem(i, 2, QtWidgets.QTableWidgetItem(""))

            color = [int(i * 255) for i in self.colors[self.labels[i]]][:3]
            item = QtWidgets.QTableWidgetItem()
            item.setBackground(QtGui.QColor(*color))
            item.setFlags(Qt.Qt.ItemIsEnabled)
            self.setItem(i, 0, item)

        self.selectAll()
        self.itemSelectionChanged.connect(self.dialog._set_data_visible)

    def select_on_weight(self):
        weights = sorted(self.comb_score_collection)
        weight = weights[self.dialog.comb_score_slider.value()]
        # First select all
        self.selectAll()
        for i in range(self.rowCount()):
            # Deselect all below weight
            if self.comb_score_collection[i] < weight:
                self.selectRow(i)

    def contextMenuEvent(self, event):
        """
        Creates the context menu for the expert widget
        """
        menu = menus.ApplyColorMenu(self, event)

    def apply_color(self, color, label):
        row = self.labels.index(label)
        # Apply to legend
        item = QtWidgets.QTableWidgetItem()
        item.setBackground(color)
        item.setFlags(Qt.Qt.ItemIsEnabled)
        self.setItem(row, 0, item)
        # Change in color overview
        itemname = self.item(row, 1).text()
        rgb = (color.redF(), color.greenF(), color.blueF())
        self.dialog.update_color(itemname, rgb)


# class CustomCanvas(FigureCanvasQTAgg):

#     def __init__(self, *args, **kwargs):
#         super(CustomCanvas, self).__init__(*args, **kwargs)

#     def draw(self):
#         print('Draw event')
#         super().draw()


class PlotExcludedDialog(QtWidgets.QDialog):
    """
    Dialog that shows the sensiticity of excluding experts or items
    from the project on the information and calibration score. The
    spread is shown by a box plot for each number of excluded experts
    or items.
    """

    def __init__(self, parent):
        """
        Constructor
        """
        super(PlotExcludedDialog, self).__init__()

        # Pointer to results and settings from ResultsOverview
        self.results = parent.results
        self.settings = parent.settings

        self.icon = parent.mainwindow.icon

        self.robustness_results = {}

        # Count number of combinations
        self.maxexclude = {
            "experts": len(self.results.experts.actual_experts) - 1,
            "items": self.results.items.get_idx("seed").sum() - 1,
        }

        self.ncombs = {}

        def nCr(n, r):
            return factorial(n) // factorial(r) // factorial(n - r)

        for typ in ["experts", "items"]:

            maxtyp = self.maxexclude[typ] + 1
            self.ncombs[typ] = np.cumsum([nCr(maxtyp, n + 1) for n in range(maxtyp)])

        self.construct_widget()

    def construct_widget(self):
        """
        Constructs the widget.
        """
        self.setWindowTitle("Robustness")
        self.setWindowIcon(self.icon)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.setLayout(QtWidgets.QVBoxLayout())

        # Create figure
        self.figure, self.ax = plt.subplots(constrained_layout=True)
        # Set background color
        bgcolor = self.palette().color(self.backgroundRole()).name()
        self.figure.patch.set_facecolor(bgcolor)
        # self.figure.tight_layout()

        self.ax.spines["right"].set_visible(False)
        self.ax.spines["top"].set_visible(False)
        self.ax.tick_params(axis="y", color="0.75")
        self.ax.tick_params(axis="x", color="0.75")

        # Add canvas
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximum(1)
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setTextVisible(False)

        # # Create comboboxes for data selection
        self.button_expert = QtWidgets.QRadioButton("Expert", clicked=self.check_maximum)
        self.button_item = QtWidgets.QRadioButton("Item", clicked=self.check_maximum)
        self.button_expert.setChecked(True)

        self.number_of_items = QtWidgets.QSpinBox()
        self.number_of_items.setMinimum(1)
        self.number_of_items.valueChanged.connect(self.get_n_combinations)
        self.ncombinations_label = QtWidgets.QLabel("Combinations: 1")
        self.check_maximum()

        self.calculate_button = QtWidgets.QPushButton("Calculate and plot", clicked=self.calculate)

        self.cat_combobox = QtWidgets.QComboBox()
        self.categories = [
            "Information score: Seed items",
            "Information score: All items",
            "Calibration score",
        ]
        self.cat_combobox.addItems(self.categories)
        self.cat_combobox.currentIndexChanged.connect(self.plot)

        rightlayout = widgets.VLayout(
            [
                widgets.SimpleGroupBox(
                    [self.button_expert, self.button_item], orientation="vertical", title="Type:"
                ),
                widgets.SimpleGroupBox(
                    [self.number_of_items, self.ncombinations_label],
                    orientation="vertical",
                    title="Number of items:",
                ),
                widgets.SimpleGroupBox(
                    [self.calculate_button, self.progress_bar], orientation="vertical", title="Calculation:"
                ),
                widgets.SimpleGroupBox([self.cat_combobox], orientation="vertical", title="Score:"),
            ]
        )
        rightlayout.addStretch(10)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.canvas)

        rightwidget = QtWidgets.QWidget()
        rightwidget.setLayout(rightlayout)
        splitter.addWidget(rightwidget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        self.layout().addWidget(splitter)

        # Add close button
        self.layout().addWidget(widgets.HLine())

        self.toolbar.setContentsMargins(0, 0, 0, 0)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.toolbar)
        button_layout.addStretch()

        # OK and Cancel buttons
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.close)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.close_button, QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(QtWidgets.QDialog.accept)
        button_layout.addWidget(button_box)

        self.layout().addLayout(button_layout)

        self.resize(800, 500)

    def update_progressbar(self):
        """
        Update the progressbar with one step, after each iteration.
        """
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def get_n_combinations(self):
        """
        Get the number of combinations for excluding the selected number of
        experts or items.
        """
        ncombs = self.ncombs[self.exclude_type][self.number_of_items.value() - 1]
        self.ncombinations_label.setText(f"Combinations: {ncombs}")
        self.progress_bar.setMaximum(min(ncombs, np.iinfo(np.int32).max))
        self.progress_bar.setValue(0)

    def calculate(self):
        # TODO: Combined score
        # TODO: Log-scale for calibration score
        # TODO: Right-click explanation box-plot
        """
        Calculate the robustness for all combinations of excluding experts. This
        method is called after the calculate button is pressed.
        """
        self.progress_bar.setValue(0)
        if self.exclude_type == "experts":
            func = self.results.calculate_expert_robustness
            dct = self.results.expert_robustness
            min_exclude = max(map(len, dct.keys())) + 1
        else:
            func = self.results.calculate_item_robustness
            dct = self.results.item_robustness
            min_exclude = max(map(len, dct.keys())) + 1

        # Call function
        if min_exclude <= self.number_of_items.value():
            # Calculate remaining number to calculate
            done = 0 if min_exclude == 1 else self.ncombs[self.exclude_type][min_exclude - 2]
            remaining = self.ncombs[self.exclude_type][self.number_of_items.value() - 1] - done
            self.progress_bar.setMaximum(remaining)
            func(
                dm_settings=self.settings,
                min_exclude=min_exclude,
                max_exclude=self.number_of_items.value(),
                progress_func=self.update_progressbar,
            )
        else:
            self.progress_bar.setValue(self.progress_bar.maximum())

        # Order results
        nbins = self.number_of_items.value()
        self.robustness_results = {cat: {i: [] for i in range(nbins + 1)} for cat in self.categories}
        for key, item in dct.items():
            nitems = len(key)
            if nitems <= nbins:
                for cat, val in zip(self.categories, item):
                    self.robustness_results[cat][nitems].append(val)
        self.plot()

    def plot(self):
        """
        Update the figure plot, called after calculation.
        """
        if not self.progress_bar.value() == self.progress_bar.maximum():
            return None

        nbins = self.number_of_items.value()
        category = self.cat_combobox.currentText()

        self.ax.clear()
        self.ax.axhline(self.robustness_results[category][0], linestyle="--", linewidth=1)
        self.ax.boxplot([self.robustness_results[category][i + 1] for i in range(nbins)])
        self.ax.set_xlim(0.5, nbins + 0.5)
        self.ax.grid(axis="y")
        self.ax.set_xlabel(f"Number of exluded {self.exclude_type} [-]")
        self.ax.set_title(category, fontsize=8, fontweight="bold")
        self.canvas.draw_idle()

    def check_maximum(self):
        """
        Gets the maximum number of calculations and sets the progess bar accordingly.
        """
        self.exclude_type = "experts" if self.button_expert.isChecked() else "items"
        self.number_of_items.setMaximum(self.maxexclude[self.exclude_type])
        self.get_n_combinations()
        self.progress_bar.setValue(0)


class CustomNavigationToolbar(NavigationToolbar2QT):
    """
    Copy of NavigationToolbar2QT class with the goal of intercepting
    the event in which the used changes the line layouts. This event
    is captured such that the colors in the legend can be adjusted accordingly
    """

    def __init__(self, canvas, qtdialog):
        super().__init__(canvas, qtdialog)
        self.qtdialog = qtdialog

    def edit_parameters(self):
        super().edit_parameters()
        for i, (_, line) in enumerate(self.qtdialog.lines.items()):
            color = line.get_color()
            item = QtWidgets.QTableWidgetItem()
            item.setBackground(QtGui.QColor(255 * color[0], 255 * color[1], 255 * color[2]))
            item.setFlags(Qt.Qt.ItemIsEnabled)
            self.qtdialog.legend.setItem(i, 0, item)


class PlotDistributionSignals(QtCore.QObject):
    """Signal class. Contains all signals that are called
    to update the GUI after changes.
    """

    clear_axis = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def connect_signals(self):
        self.clear_axis.connect(self._clear_axis)

    def _clear_axis(self):
        # Clear axis
        self.parent.ax.clear()
        self.parent.lines.clear()
        self.parent.markers.clear()
        self.parent.ax.grid()

    def connect_update_signals(self):
        """
        Connects the signals (again). This function and "disconnect_signals" are
        used to be able to change the dialog settings without updating all the figures.
        """
        self.parent.plotby_cbox.combobox.currentIndexChanged.connect(self.parent.update_plotby)
        self.parent.item_cbox.combobox.currentIndexChanged.connect(self.parent.update_plot)
        self.parent.plottype_cbox.combobox.currentIndexChanged.connect(self.parent.init_plot)

    def disconnect_update_signals(self):
        """
        Disconnects the signals (again). This function and "connect_signals" are
        used to be able to change the dialog settings without updating all the figures.
        """
        self.parent.plotby_cbox.combobox.currentIndexChanged.disconnect()
        self.parent.item_cbox.combobox.currentIndexChanged.disconnect()
        self.parent.plottype_cbox.combobox.currentIndexChanged.disconnect()


class PlotDistributionsDialog(QtWidgets.QDialog):
    """
    Dialog in which the assessments of all experts, the result
    decision maker and all items are visualized. For one item different types
    of plots can be chosen: CDF, Exceedance probability, PDF and the range.
    Per expert only the range can be shown, since the scales of each item
    varies.
    """

    def __init__(self, resultoverview):
        """
        Constructor
        """
        super(PlotDistributionsDialog, self).__init__()

        self.results = resultoverview.results
        self.icon = resultoverview.mainwindow.icon
        self.appsettings = resultoverview.mainwindow.appsettings
        # Needed to get an overview of other DM's, for adding them:
        self.resultswidget = resultoverview.resultswidget

        self.save_figure_settings = SaveFigureSettings(
            figure_type="Gridded overview",
            figure_selection="All questions",
            title_option="Full title",
            title_line_characters=40,
            save_path_overview=str(
                (Path(self.appsettings.value("currentdir", ".", type=str)) / "overview.png").resolve()
            ),
            save_directory_single_figures=str(
                Path(self.appsettings.value("currentdir", ".", type=str)).resolve()
            ),
            figure_extension=".png",
            figsize_horizontal=8,
            figsize_vertical=8,
            figure_dpi=150,
            n_axes_cols=1,
            n_axes_rows=1,
            add_legend=True,
            legend_position="lower right",
            legend_anchor=(None, None),
        )

        self.plottype = "cdf"
        self.plotby = "item"

        self.lines = {}
        self.markers = {}
        self.colors = {}

        self.colorcount = {"expert": 0, "dm": 0, "item": 0}
        self._prep_colors()

        self.signals = PlotDistributionSignals(self)
        self.construct_widget()
        self.signals.connect_signals()

        self.init_plot()

    def _prep_colors(self):

        # Create color cycle
        mpl_colors = np.array(
            [
                [0.12156862745098039, 0.4666666666666667, 0.7058823529411765],
                [1.0, 0.4980392156862745, 0.054901960784313725],
                [0.17254901960784313, 0.6274509803921569, 0.17254901960784313],
                [0.8392156862745098, 0.15294117647058825, 0.1568627450980392],
                [0.5803921568627451, 0.403921568627451, 0.7411764705882353],
                [0.5490196078431373, 0.33725490196078434, 0.29411764705882354],
                [0.8901960784313725, 0.4666666666666667, 0.7607843137254902],
                [0.4980392156862745, 0.4980392156862745, 0.4980392156862745],
                [0.7372549019607844, 0.7411764705882353, 0.13333333333333333],
                [0.09019607843137255, 0.7450980392156863, 0.8117647058823529],
            ]
        )

        self.color_cycle = []
        for alpha in [0.9, 0.65, 0.4]:
            for c in mpl_colors:
                self.color_cycle.append(tuple(1 - (1 - c) * alpha))

        for i, exp in enumerate(self.results.experts.ids):
            if i in self.results.experts.decision_makers:
                self._add_color(name=exp, itemtype="dm")
            else:
                self._add_color(name=exp, itemtype="expert")

        for i, item in enumerate(self.results.items.ids):
            self._add_color(name=item, itemtype="item")

    def _add_color(self, name, itemtype):
        assert itemtype in ["expert", "dm", "item"]
        i = self.colorcount[itemtype]
        self.colorcount[itemtype] += 1
        if itemtype in ["expert", "item"]:
            self.colors[name] = self.color_cycle[i % len(self.color_cycle)]

        elif itemtype == "dm":
            c = (i * 0.65) % 0.9
            self.colors[name] = (c, c, c)

    def update_color(self, itemname, rgb):
        """
        Update items color in color overview, legend, line and markers

        Parameters
        ----------
        itemname : str
            Name of the item, with which it is saved in the dictionaries
        """
        # Change color in overview
        self.colors[itemname] = rgb
        # Change line color in plot
        self.lines[itemname].set_color(rgb)
        # Change marker colors
        if itemname in self.markers:
            for _, m in self.markers[itemname].items():
                m.set_color(rgb)
        # Update plot
        self.canvas.draw_idle()

    def apply_callback(self):
        self.figure.apply_callback()

    def axes_layout(self):
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["top"].set_visible(False)
        self.ax.tick_params(axis="y", color="0.75")
        self.ax.tick_params(axis="x", color="0.75")

    def construct_widget(self):
        """
        Constructs the widget.
        """

        self.setWindowTitle("Distributions & range")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        self.setWindowIcon(self.icon)

        self.setLayout(QtWidgets.QVBoxLayout())

        # Create figure
        self.figure, self.ax = plt.subplots(constrained_layout=True, dpi=100)
        self.figure.apply_callback = self.apply_callback

        # Set background color
        bgcolor = self.palette().color(self.backgroundRole()).name()
        self.figure.patch.set_facecolor(bgcolor)

        self.axes_layout()

        # Add canvas
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect("scroll_event", self.scroll_dpi)
        self.toolbar = CustomNavigationToolbar(self.canvas, self)
        self.title = QtWidgets.QLabel("")
        self.title.setWordWrap(True)
        font = QtGui.QFont()
        font.setBold(True)
        self.title.setFont(font)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setContentsMargins(10, 10, 10, 10)

        self.legend = LegendTable(self)
        self.legend.setContentsMargins(0, 0, 0, 0)

        self.comb_score_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.comb_score_slider.setValue(0)
        self.comb_score_slider.setMinimum(0)
        self.comb_score_slider.setMaximum(len(self.results.experts.comb_score) - 1)
        self.comb_score_slider.valueChanged.connect(self.legend.select_on_weight)

        # DPI settings
        plus_button = QtWidgets.QPushButton("+", clicked=lambda: self.increase_dpi(factor=1.2))
        plus_button.setFixedWidth(25)
        min_button = QtWidgets.QPushButton("-", clicked=lambda: self.decrease_dpi(factor=1.2))
        min_button.setFixedWidth(25)
        self.set_dpi_box = widgets.HLayout([QtWidgets.QLabel("Scale:"), plus_button, min_button])

        # Button to save all figures
        self.save_all_button = QtWidgets.QPushButton("Save multiple figures")
        self.save_all_button.clicked.connect(self.save_all_figures)

        # Create comboboxes for data selection
        width = widgets.get_width("Anchor (x[0-1];y[0-1])")
        self.plotby_cbox = widgets.ComboboxInputLine("Plot by:", width, ["Item", "Expert"])
        self.plotby_cbox.combobox.setCurrentIndex(0)

        self.item_cbox = widgets.ComboboxInputLine("Select item:", width, self.results.items.ids)
        self.item_cbox.combobox.setCurrentIndex(0)

        self.plottype_cbox = widgets.ComboboxInputLine(
            "Select plot type:", width, ["CDF", "Exc Prob", "PDF", "Range"]
        )
        self.plottype_cbox.combobox.setCurrentIndex(0)

        self.signals.connect_update_signals()

        leftlayout = widgets.VLayout([self.title, self.canvas])

        dataselection = widgets.SimpleGroupBox(
            items=[self.plotby_cbox, self.plottype_cbox, self.item_cbox],
            orientation="vertical",
            title="Select data",
        )

        self.dm_presence = {dm: False for dm in self.resultswidget.dm_ids}
        self.dm_presence[self.results.settings.id] = True
        self.select_extra_dm = widgets.ComboboxInputLine(
            "DM:", width, [dm for dm, pr in self.dm_presence.items() if not pr]
        )

        self.add_dm_button = QtWidgets.QPushButton("Add", clicked=self.add_extra_dm_results)
        self.add_dm_groupbox = widgets.SimpleGroupBox(
            items=[widgets.HLayout([self.select_extra_dm, self.add_dm_button])],
            orientation="vertical",
            title="Add DM from other result",
        )

        rightlayout = widgets.VLayout(
            [
                dataselection,
                widgets.SimpleGroupBox([self.comb_score_slider, self.legend], "v", "Select item/expert"),
                self.add_dm_groupbox,
            ]
        )
        rightlayout.addStretch(10)

        splitter = QtWidgets.QSplitter()
        leftwidget = QtWidgets.QWidget()
        leftwidget.setLayout(leftlayout)
        splitter.addWidget(leftwidget)

        rightwidget = QtWidgets.QWidget()
        rightwidget.setLayout(rightlayout)
        splitter.addWidget(rightwidget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        self.layout().addWidget(splitter)

        # Add close button
        self.layout().addWidget(widgets.HLine())

        self.toolbar.setContentsMargins(0, 0, 0, 0)

        # OK and Cancel buttons
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.close)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.close_button, QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(QtWidgets.QDialog.accept)

        button_layout = widgets.HLayout([self.set_dpi_box, self.save_all_button, "stretch", button_box])

        self.layout().addLayout(widgets.VLayout([self.toolbar, button_layout]))

        self.resize(900, 600)

        # Initialize plot
        self.init_plot()
        self.update_plotby()

    def add_extra_dm_results(self):
        # Get selected DM
        dm_id = self.select_extra_dm.get_value()
        if dm_id == "":
            return None
        self.dm_presence[dm_id] = True
        self.select_extra_dm.combobox.removeItem(self.select_extra_dm.combobox.currentIndex())

        # Get results from other results
        extra_res = self.resultswidget.get_results(expert=dm_id)
        index = extra_res.experts.get_idx(dm_id)
        self.results.experts.add_expert(
            exp_id=extra_res.settings.id,
            exp_name=extra_res.settings.name,
            assessment=extra_res.assessments.array[index, :, :].T,
            exp_type="DM",
            full_cdf=extra_res.assessments.full_cdf[dm_id],
        )
        self._add_color(dm_id, "dm")
        self.legend.comb_score_collection.append(extra_res.experts.comb_score[index])

        # Update legend rows
        self.legend.set_rows()
        self.init_plot()

    def scroll_dpi(self, event):
        if event.button == "up":
            self.increase_dpi(factor=1.1)
        elif event.button == "down":
            self.decrease_dpi(factor=1.1)

    def increase_dpi(self, factor=1.2):
        current_dpi = self.figure.get_dpi()
        self._set_figure_dpi(current_dpi * factor)

    def decrease_dpi(self, factor=1.2):
        current_dpi = self.figure.get_dpi()
        self._set_figure_dpi(current_dpi / factor)

    def _set_figure_dpi(self, new_dpi):
        current_size = self.figure.get_size_inches()
        current_dpi = self.figure.get_dpi()

        self.figure.set_dpi(new_dpi)
        self.figure.set_size_inches(*(current_size * current_dpi / new_dpi))
        self.canvas.draw_idle()

    def init_plot(self):
        """
        Initialize the expert or items plot. Called after constructing the widget
        or after experts or items are chosen.
        """
        self.plotby = self.plotby_cbox.combobox.currentText().lower()
        self.comb_score_slider.setValue(0)

        if self.plotby == "expert":
            self.init_expert_plot()
            self.comb_score_slider.setEnabled(False)

        if self.plotby == "item":
            self.init_item_plot()
            self.comb_score_slider.setEnabled(True)

    def init_expert_plot(self):
        """
        Method to initiate expert plot
        """
        self.signals.clear_axis.emit()

        self.ax.grid()

        # Create a large list of markes for different quantiles
        selection = get_markers(self.results.assessments.quantiles)

        # Add lines for expert
        for item in self.results.items.ids:
            c = self.colors[item]
            (self.lines[item],) = self.ax.plot([], [], lw=1.5, color=c, ls="-", label=item)
            self.markers[item] = {}
            for quantile, marker in zip(self.results.assessments.quantiles, selection):
                (self.markers[item][quantile],) = self.ax.plot([], [], c=c, marker=marker, lw=0.0)

        # Add markers for realizations
        (self.lines["realization"],) = self.ax.plot([], [], c="k", marker="x", ls="", mew=2)

        # An extra draw is necessary for plotting the markers
        self.canvas.draw_idle()

        # Get first plot
        self.update_plot()

    def init_item_plot(self):
        """
        Method to initiate item plot
        """
        self.plottype = self.plottype_cbox.combobox.currentText().lower()

        # Clear axis
        self.signals.clear_axis.emit()

        # Add line for realization (only once)
        self.lines["realization"] = self.ax.axvline(np.nan, color="0.3", linestyle="--", linewidth=1.5)

        # Add lines for expert
        for expert in self.results.experts.ids:
            (self.lines[expert],) = self.ax.plot(
                [], [], lw=1.5, color=self.colors[expert], ls="-", label=expert
            )

        if self.plottype == "pdf":
            self.ax.set_ylabel("Probability density")

        if self.plottype == "cdf":
            self.ax.set_ylabel("Non-exceedance probability")

        # For range plot, add also the markers
        if self.plottype == "range":
            self.ax.set_ylabel("")

            selection = get_markers(self.results.assessments.quantiles)

            for expert in self.results.experts.ids:
                c = self.colors[expert]
                self.markers[expert] = {}
                for quantile, marker in zip(self.results.assessments.quantiles, selection):
                    (self.markers[expert][quantile],) = self.ax.plot([], [], c=c, marker=marker, lw=0.0)

            # An extra draw is necessary for plotting the markers
            self.canvas.draw_idle()

        # Get first plot
        self.update_plot()

    def update_plotby(self):
        """
        Initialize the expert or items plot type. Called after constructing the widget
        or after a different plot type is chosen.
        """

        self.plotby = self.plotby_cbox.combobox.currentText().lower()
        self.signals.disconnect_update_signals()

        # Remove current items
        for _ in range(self.plottype_cbox.combobox.count()):
            self.plottype_cbox.combobox.removeItem(0)

        for _ in range(self.item_cbox.combobox.count()):
            self.item_cbox.combobox.removeItem(0)

        if self.plotby == "expert":
            self.plottype_cbox.combobox.addItems(["Range"])
            self.item_cbox.combobox.addItems(self.results.experts.ids)
            self.add_dm_groupbox.setEnabled(False)

        elif self.plotby == "item":
            self.plottype_cbox.combobox.addItems(["CDF", "Exc Prob", "PDF", "Range"])
            self.item_cbox.combobox.addItems(self.results.items.ids)
            self.add_dm_groupbox.setEnabled(True)

        else:
            raise KeyError(self.plotby)

        self.item_cbox.combobox.setCurrentIndex(0)
        self.plottype = self.plottype_cbox.combobox.currentText().lower()
        self.signals.connect_update_signals()

        # Update legend rows
        self.legend.set_rows()
        self.init_plot()

    def update_plot(self):
        """
        Method to update a plot after changes are made to the data selection.
        """
        if self.plotby == "expert":
            self.update_expert_plot()
        elif self.plotby == "item":
            self.update_item_plot()
        else:
            raise KeyError(self.plotby)

    def update_expert_plot(self):
        """
        Method to update the expert plot after changes are made to the data selection.
        """
        # Get item data
        assessments_normed, realizations_normed = self.get_expert_data()
        # Set title
        self.set_title_xlabel()

        selected = np.unique([idx.row() for idx in self.legend.selectedIndexes()])
        items = [self.results.items.ids[i] for i in selected]
        nexp = len(selected)
        yrange = list(range(nexp))

        # Format axis
        self.format_axis(0, 1, nexp - 0.5 + 1e-6, -0.5)
        self.ax.set_yticks(yrange)
        self.ax.set_yticklabels(items)

        # Set expert lines
        for i, (idx, item) in enumerate(zip(selected, items)):
            use = self.results.items.use_quantiles[idx]
            self.lines[item].set_data(assessments_normed[idx][use], i)
            for j, quantile in enumerate(self.results.assessments.quantiles):
                self.markers[item][quantile].set_data(assessments_normed[idx][j], i)

        self.lines["realization"].set_data(realizations_normed[selected], np.arange(len(selected)) - 0.1)

        # self.figure.tight_layout()
        self.canvas.draw_idle()

    def update_item_plot(self):
        """
        Method to update the item plot after changes are made to the data selection.
        """
        # Set title
        self.set_title_xlabel()

        if self.plottype in ["cdf", "exc prob", "pdf"]:
            # Get item data
            assessments = self.get_item_data(full_dm_cdf=True)

            # Set expert lines
            quants = np.r_[0.0, self.results.assessments.quantiles, 1.0]
            ymax = 0
            for expert in self.results.experts.ids:
                plotdata = assessments[expert]
                # Plot the CDFs
                if self.plottype == "cdf":
                    ymax = 1
                    self.lines[expert].set_data(plotdata.cdf_x, plotdata.cdf_y)
                elif self.plottype == "exc prob":
                    ymax = 1
                    self.lines[expert].set_data(plotdata.cdf_x, 1 - plotdata.cdf_y)
                elif self.plottype == "pdf":
                    ymax = max(ymax, 1.1 * max(plotdata.pdf_y))
                    self.lines[expert].set_data(plotdata.pdf_x, plotdata.pdf_y)

            # Format axis
            self.format_axis(plotdata.lower, plotdata.upper, 0, ymax)
            self._set_data_visible()

        elif self.plottype == "range":
            # Get item data
            assessments = self.get_item_data(full_dm_cdf=False)

            selected = np.unique([idx.row() for idx in self.legend.selectedIndexes()])
            experts = [self.results.experts.ids[i] for i in selected]
            nexp = len(selected)
            yrange = list(range(nexp))

            # Format axis
            self.ax.set_yticks(yrange)
            self.ax.set_yticklabels(experts)

            # Set expert lines
            for i, expert in enumerate(experts):
                plotdata = assessments[expert]
                self.lines[expert].set_data(list(plotdata.estimates.values()), i)
                if expert in self.markers:

                    for quantile in self.results.assessments.quantiles:
                        if quantile in plotdata.estimates:
                            self.markers[expert][quantile].set_data(plotdata.estimates[quantile], i)
                        else:
                            self.markers[expert][quantile].set_data([], [])

            # Set axis limits for included experts
            self.format_axis(plotdata.lower, plotdata.upper, nexp - 0.5, -0.5)

        # Realization
        self.update_realization()

        # Draw
        # self.figure.tight_layout()
        self.canvas.draw_idle()

    def update_realization(self):
        """
        Set realization as line in plot.
        If target question, hide the line
        """

        # Set realization
        itemid = self.item_cbox.combobox.currentIndex()
        value = self.results.items.realizations[itemid]
        if not np.isnan(value):
            self.lines["realization"].set_visible(True)
            self.lines["realization"].set_xdata([value, value])
        else:
            self.lines["realization"].set_visible(False)

    def get_item_data(self, full_dm_cdf):
        """
        Get all the data to plot for a certain item
        """
        # Get item id
        itemid = self.item_cbox.combobox.currentIndex()

        # Get the item bounds
        lower = self.results.lower_k[itemid]
        upper = self.results.upper_k[itemid]

        # Convert bounds form log scale to uniform scale in case of log background
        if self.results.items.scales[itemid] == "log":
            lower = np.exp(lower)
            upper = np.exp(upper)

        # Get expert assessments and bounds for question
        assessments = {}
        for i, exp in enumerate(self.results.experts.ids):
            item = self.results.items.ids[itemid]
            assessments[exp] = PlotData(
                assessment=self.results.assessments.estimates[exp][item],
                quantiles=self.results.assessments.quantiles,
                distribution=self.results.settings.distribution,
                lower=lower,
                upper=upper,
                full_dm_cdf=full_dm_cdf,
            )

        return assessments

    def get_expert_data(self):
        """
        Get all the data to plot for a certain expert
        """
        # Get item id
        expertid = self.item_cbox.combobox.currentIndex()

        # Get expert assessments and bounds (no overshoot) for question
        assessments = self.results.assessments.array[expertid, :, :].T
        realizations = self.results.items.realizations.copy()
        lower = self.results.lower
        upper = self.results.upper

        # Convert bounds form log scale to uniform scale in case of log background
        for i, scale in enumerate(self.results.items.scales):
            if scale == "log":
                assessments[i, :] = np.log(assessments[i, :])
                realizations[i] = np.log(realizations[i])
                lower[i] = np.log(lower[i])
                upper[i] = np.log(upper[i])

        # Normalize assessments
        assessments = (assessments - lower[:, None]) / (upper - lower)[:, None]

        # Normalize realizations
        realizations = (realizations - lower) / (upper - lower)

        return assessments, realizations

    def format_axis(self, xmin, xmax, ymin, ymax):
        """
        Set axis limits, called after a plot has been changed.
        """
        # Get item id
        itemid = self.item_cbox.combobox.currentIndex()

        # Set x axis scale
        if self.results.items.scales[itemid] == "log":
            self.ax.set_xscale("log")
            # self.ax.set_xscale('linear')
        else:
            self.ax.set_xscale("linear")

        # Set limits
        # self.ax.axis((xmin, xmax, ymin, ymax))
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)

    def set_title_xlabel(self):
        """
        Set axis title, called after a plot has been changed.
        """
        if self.plotby == "item":
            # Get item id
            itemid = self.item_cbox.combobox.currentIndex()
            # Add to label
            self.title.setText(self.results.items.questions[itemid])
            self.ax.set_xlabel(self.results.items.units[itemid])

        elif self.plotby == "expert":
            # Get expert id
            expertid = self.item_cbox.combobox.currentIndex()
            # Add to label
            self.title.setText(self.results.experts.ids[expertid])
            self.ax.set_xlabel(None)

    def _set_data_visible(self):
        """
        Method to hide or show lines based on the selection in the legend table
        """
        # Get selected indices
        selected = [idx.row() for idx in self.legend.selectedIndexes()]

        # If plotting by item, show data for all experts
        if self.plotby == "item":
            for i, expert in enumerate(self.results.experts.ids):
                self.lines[expert].set_visible(i in selected)
                if expert in self.markers:
                    for q in self.results.assessments.quantiles:
                        self.markers[expert][q].set_visible(i in selected)

        # If plotting by expert, show data for all items
        elif self.plotby == "expert":
            for i, item in enumerate(self.results.items.ids):
                self.lines[item].set_visible(i in selected)
                for q in self.results.assessments.quantiles:
                    self.markers[item][q].set_visible(i in selected)

        # In case of a range plot, not only toggle visibility, but
        # also remove re-plot to remove 'invisible' items
        if self.plottype == "range":
            self.update_plot()

        self.canvas.draw_idle()

    def save_all_figures(self):

        self.parameters_dialog = OverviewSettingsDialog(self)
        accepted = self.parameters_dialog.exec_()

        if not accepted:
            return None

        indices = list(range(self.item_cbox.combobox.count()))
        if self.plotby == "item":
            itemtype = self.save_figure_settings.figure_selection.lower().split()[0].replace("all", "both")
            indices = [i for i, bl in zip(indices, self.results.items.get_idx(itemtype)) if bl]

        if self.save_figure_settings.figure_type == "Single figures":
            self.save_single_figures(self.save_figure_settings, indices)

        elif self.save_figure_settings.figure_type == "Gridded overview":
            self.save_overview_figure(self.save_figure_settings, indices)

    def save_single_figures(self, settings, indices):

        # Get current figure
        current = self.item_cbox.combobox.currentIndex()
        currentsize = self.figure.get_size_inches()

        if settings.title_option == "Full title":
            titletext = self.results.items.questions if self.plotby == "item" else self.results.experts.names
        elif settings.title_option == "ID title":
            titletext = self.results.items.ids if self.plotby == "item" else self.results.experts.ids
        elif settings.title_option == "No title":
            pass
        else:
            raise KeyError(settings.title_option)

        # Loop through figures and save all
        for j, i in enumerate(indices):

            self.item_cbox.combobox.setCurrentIndex(i)

            if settings.title_option != "No title":
                self.ax.set_title(
                    "\n".join(textwrap.wrap(titletext[j], width=settings.title_line_characters)),
                    fontweight="bold",
                )

            self.figure.set_size_inches(settings.figsize_horizontal / 2.54, settings.figsize_vertical / 2.54)

            # Add legend
            if settings.add_legend:
                extra = (self.add_legend(None, settings),)
            else:
                extra = ()

            naam = self.item_cbox.combobox.currentText()
            self.figure.savefig(
                settings.save_directory_single_figures / f"{i+1:02d}. {naam}{settings.figure_extension}",
                dpi=settings.figure_dpi,
                facecolor="w",
                bbox_inches="tight",
                transparent=True,
                bbox_extra_artists=extra,
            )
            if settings.add_legend:
                extra[0].remove()

        self.ax.set_title(None)
        self.figure.set_size_inches(*currentsize)

        self.item_cbox.combobox.setCurrentIndex(current)

    def save_overview_figure(self, settings, indices):

        # Create directory
        current = self.item_cbox.combobox.currentIndex()

        if settings.title_option == "Full title":
            titletext = self.results.items.questions if self.plotby == "item" else self.results.experts.names
        elif settings.title_option == "ID title":
            titletext = self.results.items.ids if self.plotby == "item" else self.results.experts.ids
        elif settings.title_option == "No title":
            pass
        else:
            raise KeyError(settings.title_option)

        overviewfig, axs = plt.subplots(
            figsize=(settings.figsize_horizontal / 2.54, settings.figsize_vertical / 2.54),
            ncols=settings.n_axes_cols,
            nrows=settings.n_axes_rows,
        )
        axs = axs.ravel()

        original_ax = self.ax

        for j, i in enumerate(indices):

            self.ax = axs[j]
            self.init_plot()
            self.item_cbox.combobox.setCurrentIndex(i)
            if settings.title_option != "No title":
                self.ax.set_title(
                    "\n".join(textwrap.wrap(titletext[i], width=settings.title_line_characters)),
                    fontweight="bold",
                )

            self.axes_layout()

        for j in range(j + 1, len(axs)):
            overviewfig.delaxes(axs[j])

        overviewfig.tight_layout()

        # Add legend
        if settings.add_legend:
            extra = (self.add_legend(overviewfig, settings),)
        else:
            extra = ()

        overviewfig.savefig(
            settings.save_path_overview,
            dpi=settings.figure_dpi,
            facecolor="w",
            bbox_inches="tight",
            transparent=True,
            bbox_extra_artists=extra,
        )

        self.ax.set_title(None)

        self.ax = original_ax

        self.item_cbox.combobox.setCurrentIndex(current)

    def add_legend(self, figure, settings):

        if self.plottype == "range":
            markers = get_markers(self.results.assessments.quantiles)
            items = [self.ax.plot([], [], marker=marker, color="0.2", ls="")[0] for marker in markers]
            lg = figure.legend(
                items,
                self.results.assessments.quantiles,
                settings.legend_position,
                title="Elicited quantiles",
                ncol=len(self.results.assessments.quantiles),
                bbox_to_anchor=settings.legend_anchor
                if ((settings.legend_anchor[0] is not None) and (settings.legend_anchor[1] is not None))
                else None,
                handlelength=1,
                columnspacing=1,
            )

        else:
            lg = self.ax.legend(
                loc=settings.legend_position,
                ncol=1,
                bbox_to_anchor=settings.legend_anchor
                if ((settings.legend_anchor[0] is not None) and (settings.legend_anchor[1] is not None))
                else None,
                # handlelength=1,
                # columnspacing=1,
            )

        return lg

    def close(self):
        for dm, pr in self.dm_presence.items():
            if (dm != self.results.settings.id) and pr:
                self.results.experts.remove_expert(dm)
        super().close()


class OverviewSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(OverviewSettingsDialog, self).__init__()

        self.appsettings = parent.appsettings
        self.icon = parent.icon

        self.results = parent.results

        self.save_figure_settings = parent.save_figure_settings
        self.ncols = self.save_figure_settings.n_axes_cols
        self.nrows = self.save_figure_settings.n_axes_rows

        self.plotby = parent.plotby
        if self.plotby == "item":
            self.nitems = {
                "All questions": sum(self.results.items.get_idx("both")),
                "Seed questions": sum(self.results.items.get_idx("seed")),
                "Target questions": sum(self.results.items.get_idx("target")),
            }
            self.nmax = self.nitems["All questions"]
            self.ncurrent = sum(self.results.items.get_idx("both"))
        else:
            self.nmax = len(self.results.experts.ids)
            self.ncurrent = self.nmax

        self.input_elements = {
            "figure": {},
            "grid_layout": {},
            "title": {},
            "saving": {},
            "legend": {},
            "exportimport": {},
        }

        self.init_ui()
        self.update_nitems()
        self.enable_figure_options()
        self.load_from_settings()

        # self.signals.connect_update_signals()
        self.connect_signals()

        self.input_elements["grid_layout"]["n_axes_cols"].set_value(int(np.ceil(self.ncurrent**0.5)))

    def accept(self):
        self.save_to_settings()
        super().accept()

    def connect_signals(self):
        for _, group in self.input_elements.items():
            for _, widget in group.items():
                if isinstance(widget, widgets.ButtonGroup):
                    widget.group.buttonClicked.connect(self.save_to_settings)
                elif isinstance(widget, widgets.ComboboxInputLine):
                    widget.combobox.currentIndexChanged.connect(self.save_to_settings)
                elif isinstance(widget, widgets.ParameterInputLine):
                    widget.LineEdit.editingFinished.connect(self.save_to_settings)
                elif isinstance(widget, widgets.DoubleParameterInputLine):
                    widget.LineEdit.editingFinished.connect(self.save_to_settings)
                    widget.LineEdit2.editingFinished.connect(self.save_to_settings)
                elif isinstance(widget, widgets.ExtendedLineEdit):
                    widget.LineEdit.editingFinished.connect(self.save_to_settings)
                elif isinstance(widget, widgets.CheckBoxInput):
                    widget.checkbox.stateChanged.connect(self.save_to_settings)

    def get_ncurrent(self):
        self.ncurrent = self.nitems[self.input_elements["figure"]["figure_selection"].get_value()]

    def update_nitems(self):
        self.get_ncurrent()
        self._adjust_nrows()

    def enable_figure_options(self):

        clicked = self.input_elements["figure"]["figure_type"].get_value(as_index=False)
        self.input_elements["grid_layout"]["n_axes_cols"].set_enabled(clicked == "Gridded overview")
        self.input_elements["grid_layout"]["n_axes_rows"].set_enabled(clicked == "Gridded overview")

    def adjust_figure_sizes(self):

        hwidget = self.input_elements["saving"]["figsize_horizontal"]
        vwidget = self.input_elements["saving"]["figsize_vertical"]

        clicked = self.input_elements["figure"]["figure_type"].get_value(as_index=False)

        if clicked == "Gridded overview":
            hwidget.set_value(float(hwidget.get_value()) * self.ncols)
            vwidget.set_value(float(vwidget.get_value()) * self.nrows)

            self.input_elements["saving"]["save_path_overview"].set_value(
                self.save_figure_settings.save_path_overview
            )

        if clicked == "Single figures":
            hwidget.set_value(float(hwidget.get_value()) / self.ncols)
            vwidget.set_value(float(vwidget.get_value()) / self.nrows)

            self.input_elements["saving"]["save_directory_single_figures"].set_value(
                self.save_figure_settings.save_directory_single_figures
            )

    def init_ui(self):

        self.setWindowTitle("Save overview figure")
        self.setWindowIcon(self.icon)
        self.setLayout(QtWidgets.QVBoxLayout())

        # Get max label width "title line characters"
        width = widgets.get_width("Title line characters")

        if self.plotby == "item":
            self.input_elements["figure"]["figure_selection"] = widgets.ComboboxInputLine(
                label="Select items",
                labelwidth=width,
                items=list(self.nitems.keys()),
                default=self.save_figure_settings.figure_selection,
            )
            self.input_elements["figure"]["figure_selection"].combobox.currentIndexChanged.connect(
                self.update_nitems
            )

        self.input_elements["figure"]["figure_type"] = widgets.ButtonGroup(
            label="Layout",
            buttonlabels=["Gridded overview", "Single figures"],
            orientation="horizontal",
            default=self.save_figure_settings.figure_type,
            labelwidth=width,
        )
        self.input_elements["figure"]["figure_type"].group.buttonClicked.connect(self.enable_figure_options)
        # self.input_elements["figure"]["figure_type"].group.buttonClicked.connect(self.adjust_figure_sizes)

        self.input_elements["grid_layout"]["n_axes_cols"] = widgets.ParameterInputLine(
            label="N columns", labelwidth=width, default=self.save_figure_settings.n_axes_cols
        )
        self.input_elements["grid_layout"]["n_axes_cols"].LineEdit.textChanged.connect(self._adjust_nrows)
        self.input_elements["grid_layout"]["n_axes_rows"] = widgets.ParameterLabel(
            label="N rows", labelwidth=width
        )

        self.input_elements["title"]["title_option"] = widgets.ButtonGroup(
            buttonlabels=["No title", "ID title", "Full title"],
            orientation="horizontal",
            label="Figure title",
            labelwidth=width,
            default=self.save_figure_settings.title_option,
        )
        self.input_elements["title"]["title_line_characters"] = widgets.ParameterInputLine(
            label="Title line characters", labelwidth=width, default=40
        )
        self.input_elements["saving"]["save_path_overview"] = widgets.ExtendedLineEdit(
            label="Save location",
            labelwidth=width,
            browsebutton=QtWidgets.QPushButton("...", clicked=self._get_path),
        )
        self.input_elements["saving"]["save_directory_single_figures"] = self.input_elements["saving"][
            "save_path_overview"
        ]

        self.input_elements["saving"]["figure_extension"] = widgets.ComboboxInputLine(
            label="Figure extension",
            labelwidth=width,
            items=[".png", ".jpg", ".pdf"],
            default=self.save_figure_settings.figure_extension,
        )
        self.input_elements["saving"]["figure_extension"].combobox.currentIndexChanged.connect(
            self._change_ext
        )

        self.input_elements["saving"]["figsize_horizontal"] = widgets.ParameterInputLine(
            label="Hor. size (cm)",
            labelwidth=width,
            default=self.save_figure_settings.figsize_horizontal,
            validator=QtGui.QDoubleValidator(1.00, 1000.00, 20),
        )
        self.input_elements["saving"]["figsize_vertical"] = widgets.ParameterInputLine(
            label="Vert. size (cm)",
            labelwidth=width,
            default=self.save_figure_settings.figsize_vertical,
            validator=QtGui.QDoubleValidator(1.00, 1000.00, 20),
        )
        self.input_elements["saving"]["figure_dpi"] = widgets.ParameterInputLine(
            label="DPI",
            labelwidth=width,
            default=self.save_figure_settings.figure_dpi,
            validator=QtGui.QIntValidator(10, 2400),
        )

        self.input_elements["legend"]["add_legend"] = widgets.CheckBoxInput(
            label="Add legend", labelwidth=width, default=self.save_figure_settings.add_legend
        )

        self.input_elements["legend"]["legend_position"] = widgets.ComboboxInputLine(
            label="Position",
            labelwidth=width,
            default=self.save_figure_settings.legend_position,
            items=[
                "upper right",
                "upper left",
                "lower left",
                "lower right",
                "right",
                "center left",
                "center right",
                "lower center",
                "upper center",
                "center",
            ],
        )
        # regexp = QtCore.QRegExp("^\d+(?:[\.\,]\d+)?[;]\d+(?:[\.\,]\d+)?$")
        v1, v2 = self.save_figure_settings.legend_anchor
        self.input_elements["legend"]["legend_anchor"] = widgets.DoubleParameterInputLine(
            label="Anchor (x[0-1];y[0-1])",
            labelwidth=width,
            validator1=QtGui.QDoubleValidator(0.0, 1.0, 20),
            validator2=QtGui.QDoubleValidator(0.0, 1.0, 20),
            default1=str(v1) if v1 is not None else "",
            default2=str(v2) if v2 is not None else "",
        )

        self.input_elements["exportimport"]["save_settings"] = QtWidgets.QPushButton(
            "Export settings", clicked=self._export_settings
        )
        self.input_elements["exportimport"]["load_settings"] = QtWidgets.QPushButton(
            "Import settings", clicked=self._import_settings
        )

        titles = {
            "figure": "Figure options",
            "legend": "Legend settings",
            "saving": "Save options",
            "grid_layout": "Grid layout",
            "title": "Title options",
            "exportimport": "Settings export/import",
        }

        for i, (key, dct) in enumerate(self.input_elements.items()):

            groupbox = widgets.SimpleGroupBox(list(dct.values()), "vertical", titles[key])

            self.layout().addWidget(groupbox)

        # OK and Cancel buttons
        self.save_button = QtWidgets.QPushButton("Save figure(s)")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.accept)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.save_button, QtWidgets.QDialogButtonBox.ActionRole)
        button_box.addButton(self.cancel_button, QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(QtWidgets.QDialog.accept)

        self.layout().addWidget(button_box)

    def _adjust_nrows(self):
        ncols_old = self.ncols
        nrows_old = self.nrows

        # Change number of rows based on number of columns
        self.ncols = int(self.input_elements["grid_layout"]["n_axes_cols"].get_value())
        self.nrows = int(np.ceil(self.ncurrent / self.ncols))
        self.input_elements["grid_layout"]["n_axes_rows"].set_value(self.nrows)

        # Change figure sizes based on new layout
        hwidget = self.input_elements["saving"]["figsize_horizontal"]
        vwidget = self.input_elements["saving"]["figsize_vertical"]

        figure_type = self.input_elements["figure"]["figure_type"].get_value(as_index=False)
        # if figure_type == "Gridded overview":
        #     hwidget.set_value(float(hwidget.get_value()) * (self.ncols / ncols_old))
        #     vwidget.set_value(float(vwidget.get_value()) * (self.nrows / nrows_old))

    def _get_path(self):

        # Set open file dialog settings
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtWidgets.QFileDialog.DontConfirmOverwrite
        # options |= QtWidgets.QFileDialog.DirectoryOnly

        # Set current dir
        currentdir = self.appsettings.value("currentdir", ".", type=str)

        if self.input_elements["figure"]["figure_type"].get_value() == "Single figures":
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Anduryl - Select directory for saving figures",
                currentdir,
                options=options,
            )
            self.input_elements["saving"]["save_path_overview"].set_value(directory)

        elif self.input_elements["figure"]["figure_type"].get_value() == "Gridded overview":

            # Open dialog to select file
            fname, ext = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Anduryl - Select location for saving figure",
                currentdir,
                "PNG (*.png);;JPEG (*.jpg);;PDF (*.pdf)",
                options=options,
            )
            ext = ext.split("*")[-1][:-1]
            if not fname.endswith(ext):
                fname += ext

            self.input_elements["saving"]["save_directory_single_figures"].set_value(fname)
            self.input_elements["saving"]["figure_extension"].set_value(ext)

    def _export_settings(self):

        self.save_to_settings()

        # Set open file dialog settings
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        # options |= QtWidgets.QFileDialog.DirectoryOnly

        # Set current dir
        currentdir = self.appsettings.value("currentdir", ".", type=str)

        # Open dialog to select file
        fname, ext = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Anduryl - Select file location for exporting figure settings",
            currentdir,
            "JSON (*.json)",
            options=options,
        )
        ext = ext.split("*")[-1][:-1]
        if not fname.endswith(ext):
            fname += ext

        if fname == "":
            return

        with open(fname, "w") as f:
            f.write(self.save_figure_settings.json(indent=4))

    def _import_settings(self):

        # Set open file dialog settings
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog

        # Set current dir
        currentdir = self.appsettings.value("currentdir", ".", type=str)

        # Open dialog to select file
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption="Anduryl - Select file location with figure settings to import",
            directory=currentdir,
            filter="JSON (*.json)",
            options=options,
        )

        if fname == "":
            return

        with open(fname) as f:
            for key, value in json.load(f).items():
                setattr(self.save_figure_settings, key, value)
            self.load_from_settings()

    def _change_ext(self):

        # Check if savetype is gridded overview
        if self.input_elements["figure"]["figure_type"].get_value() == "Gridded overview":
            # If so, replace extension with new one
            new_ext = self.input_elements["saving"]["figure_extension"].combobox.currentText()
            widget = self.input_elements["saving"]["save_path_overview"]
            current = widget.get_value()
            widget.set_value(current[: current.rfind(".")] + new_ext)

    def save_to_settings(self):
        """
        Save parameters to settings. The settings have the same layout as the input_elements dict
        """
        for _, group in self.input_elements.items():
            for param, widget in group.items():
                if hasattr(widget, "get_value"):
                    val = widget.get_value()
                    if param == "save_path_overview":
                        if self.save_figure_settings.figure_type == "Gridded overview":
                            self.save_figure_settings.save_path_overview = val

                    elif param == "save_directory_single_figures":
                        if self.save_figure_settings.figure_type == "Single figures":
                            self.save_figure_settings.save_directory_single_figures = val

                    else:
                        setattr(self.save_figure_settings, param, val)

    def load_from_settings(self):
        """
        Save parameters to settings. The settings have the same layout as the input_elements dict
        """
        for param, value in self.save_figure_settings._iter():
            # Some settings do not have a GUI element, continue if encountered
            groups = [group_name for group_name, group in self.input_elements.items() if param in group]
            assert len(groups) == 1
            group_name = groups[0]

            if self.save_figure_settings.figure_type == "Gridded overview" and param == "save_path_overview":
                self.input_elements[group_name][param].set_value(self.save_figure_settings.save_path_overview)
            elif (
                self.save_figure_settings.figure_type == "Single figures"
                and param == "save_directory_single_figures"
            ):
                self.input_elements[group_name][param].set_value(
                    self.save_figure_settings.save_directory_single_figures
                )
            else:
                self.input_elements[group_name][param].set_value(value)


class ItemWeightDialog(QtWidgets.QDialog):
    """
    Dialog to get parameters for calculating decision maker
    """

    def __init__(self, parent):
        """
        Constructor
        """
        super(ItemWeightDialog, self).__init__()

        results = parent.results

        self.setWindowTitle("Information score per item")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)

        self.setLayout(QtWidgets.QVBoxLayout())

        # Add checkbox for colors
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(QtWidgets.QLabel("Colormap:"))
        self.colorbutton = QtWidgets.QCheckBox()
        self.colorbutton.setChecked(False)
        self.colorbutton.clicked.connect(self.set_color)
        hlayout.addWidget(self.colorbutton)
        self.layout().addLayout(hlayout)

        # Create the table view
        self.table = QtWidgets.QTableView()
        self.table.verticalHeader().setVisible(True)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        # Create and add model
        self.array = results.experts.info_per_var
        self.model = ArrayModel(
            array=self.array,
            labels=[results.experts.ids, results.items.ids],
            coldim=0,
            rowdim=[1],
            index_names=["Expert"],
            index=True,
        )
        self.model.colorpicker = self.colorpicker
        self.table.setModel(self.model)

        self.layout().addWidget(self.table)
        self.table.horizontalHeader().setMinimumSectionSize(70)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        # Add close button
        self.layout().addWidget(widgets.HLine())

        # OK and Cancel buttons
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.close)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.close_button, QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(QtWidgets.QDialog.accept)

        self.layout().addWidget(button_box)

        self.resize(100 + 100 * min(len(results.experts.ids), 10), 600)

        self.arrmin = self.array.min()
        self.arrmax = self.array.max()

        self.cmap = cm.get_cmap("RdYlGn")

    def colorpicker(self, idx):
        """
        Returns a color for assigning to the cell
        """
        value = self.array[idx]
        return self.cmap((value - self.arrmin) / (self.arrmax - self.arrmin))

    def set_color(self):
        """
        Changed the table settings after colors are toggled on or off
        """
        on = self.colorbutton.isChecked()
        self.model.layoutAboutToBeChanged.emit()
        self.model.colored = on
        self.table.setShowGrid(on)
        self.table.setAlternatingRowColors(not on)
        self.model.layoutChanged.emit()
