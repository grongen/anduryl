import copy
from itertools import combinations
from math import factorial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg,
                                                NavigationToolbar2QT)
from matplotlib.figure import Figure
from PyQt5 import Qt, QtCore, QtGui, QtWidgets

from anduryl import io
from anduryl.ui import widgets
from anduryl.ui.dialogs import NotificationDialog
from anduryl.ui.models import ArrayModel, ListsModel

plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['axes.labelsize'] = 9
plt.rcParams['axes.titlesize'] = 9
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['grid.alpha'] = 0.25
plt.rcParams['legend.handletextpad'] = 0.4
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['legend.labelspacing'] = 0.2
plt.rcParams['font.size'] = 9
plt.rcParams['figure.dpi'] = 50

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

        label = QtWidgets.QLabel('Results')
        label.setContentsMargins(5, 2.5, 5, 2.5)
        label.setStyleSheet("QLabel {border: 1px solid "+self.mainwindow.bordercolor+"}")
        
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
        resultsoverview = ResultOverview(self.mainwindow, results)

        # Add to tabs        
        self.tabs.addTab(resultsoverview, resultid + ' (' + results.settings['name'] + ')')
        self.dm_ids.append(resultid)

        # Add to export menu
        self.mainwindow.add_export_actions(resultsoverview)

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
    
    def __init__(self, mainwindow, results):
        """
        Copy results from current project. Note that the results are copied
        and not refered to, since we want to 'freeze' the current project in
        these results. 
        """

        super(ResultOverview, self).__init__()

        self.mainwindow = mainwindow
        
        # TODO Copy results and settings
        self.results = results
        self.settings = self.results.settings
        
        # Calculate lower bounds once. Since these results are frozen the bounds won't change
        self.results.lower_k, self.results.upper_k = self.results.assessments.get_bounds(overshoot=self.settings['overshoot'])
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
        label_layout.addWidget(QtWidgets.QLabel(f"Weights: {self.settings['weight']}"), 0, 0)
        label_layout.addWidget(QtWidgets.QLabel(f"Optimisation: {'yes' if self.settings['optimisation'] else 'no'}"), 0, 1)
        label_layout.addWidget(QtWidgets.QLabel(f"Intrinsic range: {self.settings['overshoot']}"), 0, 2)
        label_layout.addWidget(QtWidgets.QLabel(f"Significance level: {self.results.alpha_opt:.4g}"), 1, 0)
        label_layout.addWidget(QtWidgets.QLabel(f"Calibration power: {self.settings['calpower']}"), 1, 1)

        self.plot_items_button = QtWidgets.QPushButton('Plot items', clicked=self.plot_items)
        self.plot_items_button.setFixedWidth(100)
        
        layout.addWidget(widgets.SimpleGroupBox([label_layout, self.plot_items_button], 'vertical', 'Decision maker characteristics'))

        # Add table with expert results (weights etcetera)
        table = self.add_expert_weights_table()

        self.show_item_weights_button = QtWidgets.QPushButton('Info score per item', clicked=self.show_items)
        self.show_item_weights_button.setFixedWidth(100)

        layout.addWidget(widgets.SimpleGroupBox([table, self.show_item_weights_button], 'vertical', 'Expert and DM weights'))
        
        # Add a table for the item robustness
        if self.results.item_robustness or self.results.expert_robustness:
            self.robustness_tables = QtWidgets.QTabWidget()
        
            if self.results.item_robustness:
                seedidx = self.results.items.get_idx('seed')
                seeditems = [None] + [item for i, item in enumerate(self.results.items.ids) if seedidx[i]]
                item_array = np.vstack([self.results.item_robustness[tuple([itemid] if itemid is not None else [])] for itemid in seeditems])
                seeditems[0] = 'None'

                self.ui_add_robustness_table('Items', seeditems, item_array)

            if self.results.expert_robustness:
                experts = [None] + self.results.experts.get_exp('actual')
                expert_array = np.vstack([self.results.expert_robustness[tuple([exp] if exp is not None else [])] for exp in experts]) 
                experts[0] = 'None'

                self.ui_add_robustness_table('Experts', experts, expert_array)

            # Plot layout
            self.plot_excluded_button = QtWidgets.QPushButton('Plot multiple exluded items', clicked=self.plot_excluded_items)
            button_layout = widgets.HLayout([self.plot_excluded_button])
            button_layout.addStretch()
            layout.addWidget(widgets.SimpleGroupBox([self.robustness_tables, button_layout], 'vertical', 'Robustness'))

        layout.addStretch()

    def add_expert_weights_table(self):
        # Create the table view
        table = QtWidgets.QTableView()
        self.scores_table = table
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        
        # Get weights
        if self.settings['weight'].lower() in ['global', 'item']:
            weights = self.results.experts.weights.copy()

        elif self.settings['weight'].lower() == 'equal':
            n = len(self.results.experts.actual_experts)
            weights = np.ones_like(self.results.experts.weights) / n

        elif self.settings['weight'].lower() == 'user':
            weights = np.zeros_like(self.results.experts.weights)
            idx = ~np.isnan(self.results.experts.user_weights)
            idx[self.results.experts.get_idx('dm')] = False
            weights[idx] += self.results.experts.user_weights[idx] / self.results.experts.user_weights[idx].sum()

        # Correct for alpha threshold
        weights[self.results.experts.calibration < self.results.alpha_opt] = 0.0

        # Set DM to zero
        dm_idx = self.results.experts.get_idx('dm')
        weights[dm_idx] = np.nan

        # Create and add model
        self.scores_model = ListsModel(
            lists=[
                self.results.experts.ids,
                self.results.experts.names,
                self.results.experts.calibration,
                self.results.experts.info_real,
                self.results.experts.info_total,
                weights                
            ],
            labels=['ID', 'Name', 'Calibration', 'Info score real.', 'Info score total', 'Weight']
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
            labels=[index, ['Info score total', 'Info score real.', 'Calibration']],
            coldim=1,
            rowdim=[0],
            index_names=['Item ID'],
            index=True
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
        if (event.type() == QtCore.QEvent.KeyPress and event.matches(QtGui.QKeySequence.Copy)):
            selection = source.selectedIndexes()
            if selection:
                text = io.selection_to_text(selection)
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
        self.setHorizontalHeaderLabels(['', 'Expert', 'Weight'])
        self.setColumnWidth(0, 10)
        
        self.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.setSelectionMode(QtWidgets.QTableWidget.MultiSelection)
        
        p = QtGui.QPalette()
        # Both active and inactive should follow inactive layout
        for group in [QtGui.QPalette.Active, QtGui.QPalette.Inactive]:
            # Switch background
            p.setColor(group, QtGui.QPalette.Highlight, p.color(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight))
            # p.setColor(group, QtGui.QPalette.Base, p.color(QtGui.QPalette.Inactive, QtGui.QPalette.Base))
            
            # Set text colors
            p.setColor(group, QtGui.QPalette.HighlightedText, p.color(QtGui.QPalette.Inactive, QtGui.QPalette.HighlightedText))            
            p.setColor(group, QtGui.QPalette.Text, p.color(QtGui.QPalette.Inactive, QtGui.QPalette.Dark))
        self.setPalette(p)

        self.itemSelectionChanged.connect(self.dialog._set_data_visible)
        self.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

    def set_rows(self):
        """
        Fill in the legend with all the expert id's and weights
        """

        plotby = self.dialog.plotby_cbox.combobox.currentText().lower()
        if plotby == 'expert':
            items = self.results.items.ids
            self.setHorizontalHeaderLabels(['', 'Item', ''])
        elif plotby == 'item':
            items = self.results.experts.ids
            self.setHorizontalHeaderLabels(['', 'Expert', 'Weight'])
        else:
            raise KeyError(plotby)

        nrows = len(items)
        
        self.setFixedHeight(min(24 * (nrows + 1), 400))

        self.itemSelectionChanged.disconnect()

        self.setRowCount(nrows)

        for i in range(nrows):
            self.setItem(i, 1, QtWidgets.QTableWidgetItem(items[i]))
            if plotby == 'item':
                self.setItem(i, 2, QtWidgets.QTableWidgetItem(f'{self.results.experts.weights[i]:.4g}'))
            if plotby == 'expert':
                self.setItem(i, 2, QtWidgets.QTableWidgetItem(''))
            
            color = [int(i* 255) for i in self.colors[items[i]]][:3]
            item = QtWidgets.QTableWidgetItem()
            item.setBackground(QtGui.QColor(*color))
            item.setFlags(Qt.Qt.ItemIsEnabled)
            self.setItem(i, 0, item)

        self.selectAll()
        self.itemSelectionChanged.connect(self.dialog._set_data_visible)

    def select_on_weight(self):
        weights = sorted(self.results.experts.weights)
        weight = weights[self.dialog.weightslider.value()]
        # First select all
        self.selectAll()
        for i in range(self.rowCount()):
            # Deselect all below weight
            if self.results.experts.weights[i] < weight:
                self.selectRow(i)



    def contextMenuEvent(self, event):
        """
        Creates the context menu for the expert widget
        """
        menu = QtWidgets.QMenu(self)
        
        # Get current row
        rownum = self.currentIndex().row()
        # decision_maker_selected = (rownum in self.project.experts.decision_makers)
        
        # Add actions
        pick_color_action = menu.addAction("Pick color")
        
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == pick_color_action:
            self.pick_color(rownum)

    def pick_color(self, row):
        color = QtWidgets.QColorDialog.getColor()
        item = QtWidgets.QTableWidgetItem()
        item.setBackground(color)
        item.setFlags(Qt.Qt.ItemIsEnabled)
        self.setItem(row, 0, item)

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
            'experts': len(self.results.experts.actual_experts) - 1,
            'items': self.results.items.get_idx('seed').sum() - 1
        }
        
        self.ncombs = {}
        def nCr(n, r):
            return factorial(n) // factorial(r) // factorial(n-r)
        
        for typ in ['experts', 'items']:

            maxtyp = self.maxexclude[typ] + 1
            self.ncombs[typ] = np.cumsum([nCr(maxtyp, n+1) for n in range(maxtyp)])
            
        self.construct_widget()

    def construct_widget(self):
        """
        Constructs the widget.
        """
        self.setWindowTitle('Robustness')
        self.setWindowIcon(self.icon)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.setLayout(QtWidgets.QVBoxLayout())

        # Create figure
        self.figure, self.ax = plt.subplots(constrained_layout=True)
        # Set background color
        bgcolor = self.palette().color(self.backgroundRole()).name()
        self.figure.patch.set_facecolor(bgcolor)
        # self.figure.tight_layout()

        self.ax.spines['right'].set_visible(False)
        self.ax.spines['top'].set_visible(False)
        self.ax.tick_params(axis='y', color='0.75')
        self.ax.tick_params(axis='x', color='0.75')
        
        # Add canvas
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximum(1)
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setTextVisible(False)
        
        # # Create comboboxes for data selection
        self.button_expert = QtWidgets.QRadioButton('Expert', clicked=self.check_maximum)
        self.button_item = QtWidgets.QRadioButton('Item', clicked=self.check_maximum)
        self.button_expert.setChecked(True)
            
        self.number_of_items = QtWidgets.QSpinBox()
        self.number_of_items.setMinimum(1)
        self.number_of_items.valueChanged.connect(self.get_n_combinations)
        self.ncombinations_label = QtWidgets.QLabel('Combinations: 1')
        self.check_maximum()

        self.calculate_button = QtWidgets.QPushButton('Calculate and plot', clicked=self.calculate)

        self.cat_combobox = QtWidgets.QComboBox()
        self.categories = ['Information score: Seed items', 'Information score: All items', 'Calibration score']
        self.cat_combobox.addItems(self.categories)
        self.cat_combobox.currentIndexChanged.connect(self.plot)
        
        rightlayout = widgets.VLayout([
            widgets.SimpleGroupBox([self.button_expert, self.button_item], orientation='vertical', title='Type:'),
            widgets.SimpleGroupBox([self.number_of_items, self.ncombinations_label], orientation='vertical', title='Number of items:'),
            widgets.SimpleGroupBox([self.calculate_button, self.progress_bar], orientation='vertical', title='Calculation:'),
            widgets.SimpleGroupBox([self.cat_combobox], orientation='vertical', title='Score:'),
        ])
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
        self.close_button = QtWidgets.QPushButton('Close')
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
        ncombs = self.ncombs[self.exclude_type][self.number_of_items.value()-1]
        self.ncombinations_label.setText(f'Combinations: {ncombs}')
        self.progress_bar.setMaximum(min(ncombs, np.iinfo(np.int32).max))
        self.progress_bar.setValue(0)
        
    def calculate(self):
        """
        Calculate the robustness for all combinations of excluding experts. This
        method is called after the calculate button is pressed.
        """
        self.progress_bar.setValue(0)
        if self.exclude_type == 'experts':
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
            done = 0 if min_exclude == 1 else self.ncombs[self.exclude_type][min_exclude-2]
            remaining = self.ncombs[self.exclude_type][self.number_of_items.value()-1] - done
            self.progress_bar.setMaximum(remaining)
            func(
                min_exclude=min_exclude,
                max_exclude=self.number_of_items.value(),
                weight_type=self.settings['weight'].lower(),
                overshoot=self.settings['overshoot'],
                alpha=self.settings['alpha'],
                calpower=self.settings['calpower'],
                progress_func=self.update_progressbar
            )
        else:
            self.progress_bar.setValue(self.progress_bar.maximum())

        # Order results
        nbins = self.number_of_items.value()
        self.robustness_results = {cat: {i: [] for i in range(nbins+1)} for cat in self.categories}
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
        self.ax.axhline(self.robustness_results[category][0], linestyle='--', linewidth=1)
        self.ax.boxplot([self.robustness_results[category][i+1] for i in range(nbins)])
        self.ax.set_xlim(0.5, nbins+0.5)
        self.ax.grid(axis='y')
        self.ax.set_xlabel(f'Number of exluded items {self.exclude_type} [-]')
        self.ax.set_title(category, fontsize=8, fontweight='bold')
        self.canvas.draw_idle()

    def check_maximum(self):
        """
        Gets the maximum number of calculations and sets the progess bar accordingly.
        """
        self.exclude_type = 'experts' if self.button_expert.isChecked() else 'items'
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
            item.setBackground(QtGui.QColor(255*color[0], 255*color[1], 255*color[2]))
            item.setFlags(Qt.Qt.ItemIsEnabled)
            self.qtdialog.legend.setItem(i, 0, item)
        
class PlotDistributionsDialog(QtWidgets.QDialog):
    """
    Dialog in which the assessments of all experts, the result
    decision maker and all items are visualized. For one item different types
    of plots can be chosen: CDF, Exceedance probability, PDF and the range.
    Per expert only the range can be shown, since the scales of each item
    varies.
    """

    def __init__(self, parent):
        """
        Constructor
        """
        super(PlotDistributionsDialog, self).__init__()

        self.results = parent.results
        self.icon = parent.mainwindow.icon
        self.plottype = 'cdf'
        self.plotby = 'item'

        self.lines = {}
        self.markers = {}
        self.colors = {}

        # Create color cycle
        mpl_colors = np.array([
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
        ])

        color_cycle = []
        for alpha in [0.9, 0.65, 0.4]:
            for c in mpl_colors:
                color_cycle.append(tuple(1 - (1 - c) * alpha))

        for i, exp in enumerate(self.results.experts.ids):
            if i in self.results.experts.decision_makers:
                self.colors[exp] = (0, 0, 0)
            else:
                self.colors[exp] = color_cycle[i%len(color_cycle)]
            
        for i, item in enumerate(self.results.items.ids):
            self.colors[item] = color_cycle[i%len(color_cycle)]

        self.construct_widget()

        self.init_plot()

    def apply_callback(self):
        self.figure.apply_callback()

    def construct_widget(self):
        """
        Constructs the widget.
        """

        self.setWindowTitle('Distributions & range')
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        self.setWindowIcon(self.icon)

        self.setLayout(QtWidgets.QVBoxLayout())

        # Create figure
        self.figure, self.ax = plt.subplots(constrained_layout=True)
        self.figure.apply_callback = self.apply_callback
        
        # Set background color
        bgcolor = self.palette().color(self.backgroundRole()).name()
        self.figure.patch.set_facecolor(bgcolor)
        # self.figure.tight_layout()

        self.ax.spines['right'].set_visible(False)
        self.ax.spines['top'].set_visible(False)
        self.ax.tick_params(axis='y', color='0.75')
        self.ax.tick_params(axis='x', color='0.75')
        
        # Add canvas
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = CustomNavigationToolbar(self.canvas, self)
        self.title = QtWidgets.QLabel('')
        self.title.setWordWrap(True)
        font=QtGui.QFont()
        font.setBold(True)
        self.title.setFont(font)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setContentsMargins(10, 10, 10, 10)

        self.legend = LegendTable(self)
        self.legend.setContentsMargins(0, 0, 0, 0)
        
        self.weightslider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.weightslider.setValue(0)
        self.weightslider.setMinimum(0)
        self.weightslider.setMaximum(len(self.results.experts.weights)-1)
        self.weightslider.valueChanged.connect(self.legend.select_on_weight)
        
        # Create comboboxes for data selection
        self.plotby_cbox = widgets.ComboboxInputLine('Plot by:', 100, ['Item', 'Expert'])
        self.plotby_cbox.combobox.setCurrentIndex(0)

        self.item_cbox = widgets.ComboboxInputLine('Select item:', 100, self.results.items.ids)
        self.item_cbox.combobox.setCurrentIndex(0)

        self.plottype_cbox = widgets.ComboboxInputLine('Select plot type:', 100, ['CDF', 'Exc Prob', 'PDF', 'Range'])
        self.plottype_cbox.combobox.setCurrentIndex(0)

        self.connect_signals()

        # Initialize plot
        self.init_plot()
        self.update_plotby()

        leftlayout = widgets.VLayout([self.title, self.canvas])
        
        dataselection = widgets.SimpleGroupBox(
            items=[self.plotby_cbox, self.plottype_cbox, self.item_cbox], orientation='vertical', title='Select data')
        
        rightlayout = widgets.VLayout([dataselection, widgets.SimpleGroupBox([self.weightslider, self.legend], 'v', 'Select item/expert')])        
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
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.toolbar)
        button_layout.addStretch()

        # OK and Cancel buttons
        self.close_button = QtWidgets.QPushButton('Close')
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.close)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.close_button, QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(QtWidgets.QDialog.accept)
        button_layout.addWidget(button_box)

        self.layout().addLayout(button_layout)

        self.resize(900, 600)

    def connect_signals(self):
        """
        Connects the signals (again). This function and "disconnect_signals" are
        used to be able to change the dialog settings without updating all the figures.
        """
        self.plotby_cbox.combobox.currentIndexChanged.connect(self.update_plotby)
        self.item_cbox.combobox.currentIndexChanged.connect(self.update_plot)
        self.plottype_cbox.combobox.currentIndexChanged.connect(self.init_plot)
        
    def disconnect_signals(self):
        """
        Disconnects the signals (again). This function and "connect_signals" are
        used to be able to change the dialog settings without updating all the figures.
        """
        self.plotby_cbox.combobox.currentIndexChanged.disconnect()
        self.item_cbox.combobox.currentIndexChanged.disconnect()
        self.plottype_cbox.combobox.currentIndexChanged.disconnect()

    def init_plot(self):
        """
        Initialize the expert or items plot. Called after constructing the widget
        or after experts or items are chosen.
        """
        self.plotby = self.plotby_cbox.combobox.currentText().lower()
        self.weightslider.setValue(0)

        if self.plotby == 'expert':
            self.init_expert_plot()
            self.weightslider.setEnabled(False)
        if self.plotby == 'item':
            self.init_item_plot()
            self.weightslider.setEnabled(True)
        
    def init_expert_plot(self):
        """
        Method to initiate expert plot
        """
        # Clear axis
        self.ax.clear()
        self.lines.clear()
        self.markers.clear()

        self.ax.grid()

        # Create a large list of markes for different quantiles        
        markers = ['2', '^', '*', 'h', 'd', 's', 'o', 'X', 'o', 's', 'd', 'h', '*', '^', '2']
        # The offset gives the markers to use in the list, so for three markers, the first 6 are skipped
        offset = (len(markers) - len(self.results.assessments.quantiles)) // 2
        selection = markers[offset:-offset]
        
        # Add lines for expert
        for item in self.results.items.ids:
            c = self.colors[item]
            self.lines[item], = self.ax.plot([], [], lw=2.0, color=c, ls='-', label=item)
            self.markers[item] = {}
            for quantile, marker in zip(self.results.assessments.quantiles, selection):
                self.markers[item][quantile], = self.ax.plot([], [], c=c, marker=marker, ms=5)

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
        self.ax.clear()
        self.lines.clear()
        self.markers.clear()

        self.ax.grid()
        # Add line for realization (only once)
        self.lines['realization'] = self.ax.axvline(np.nan, color='0.3', linestyle='--', linewidth=1.5)

        # Add lines for expert
        for expert in self.results.experts.ids:
            self.lines[expert], = self.ax.plot([], [], lw=2.0, color=self.colors[expert], ls='-', label=expert)

        if self.plottype == 'pdf':
            self.ax.set_ylabel('Probability density')
        
        if self.plottype == 'cdf':
            self.ax.set_ylabel('Non-exceedance probability')

        # For range plot, add also the markers
        if self.plottype == 'range':
            self.ax.set_ylabel('')

            markers = ['2', '^', '*', 'h', 'd', 's', 'o', 'X', 'o', 's', 'd', 'h', '*', '^', '2']
            offset = (len(markers) - len(self.results.assessments.quantiles)) // 2
            selection = markers[offset:-offset]

            for expert in self.results.experts.ids:
                c = self.colors[expert]
                self.markers[expert] = {}
                for quantile, marker in zip(self.results.assessments.quantiles, selection):
                    self.markers[expert][quantile], = self.ax.plot([], [], c=c, marker=marker, ms=5)

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
        self.disconnect_signals()
        
        # Remove current items
        for i in range(self.plottype_cbox.combobox.count()):
            self.plottype_cbox.combobox.removeItem(0)
            
        for i in range(self.item_cbox.combobox.count()):
            self.item_cbox.combobox.removeItem(0)

        if self.plotby == 'expert':
            self.plottype_cbox.combobox.addItems(['Range'])
            self.item_cbox.combobox.addItems(self.results.experts.ids)

        elif self.plotby == 'item':
            self.plottype_cbox.combobox.addItems(['CDF', 'Exc Prob', 'PDF', 'Range'])
            self.item_cbox.combobox.addItems(self.results.items.ids)
        
        else:
            raise KeyError(self.plotby)
        
        self.item_cbox.combobox.setCurrentIndex(0)
        self.plottype = self.plottype_cbox.combobox.currentText().lower()
        self.connect_signals()
        
        # Update legend rows
        self.legend.set_rows()
        self.init_plot()

    def update_plot(self):
        """
        Method to update a plot after changes are made to the data selection.
        """
        if self.plotby == 'expert':
            self.update_expert_plot()
        elif self.plotby == 'item':
            self.update_item_plot()
        else:
            raise KeyError(self.plotby)

    def update_expert_plot(self):
        """
        Method to update the expert plot after changes are made to the data selection.
        """
        # Get item data
        assessments = self.get_expert_data()
        # Set title
        self.set_title()

        selected = np.unique([idx.row() for idx in self.legend.selectedIndexes()])
        items = [self.results.items.ids[i] for i in selected]
        nexp = len(selected)
        yrange = list(range(nexp))
        
        # Format axis
        self.format_axis(0, 1, -0.5, nexp-0.5 + 1e-6)
        self.ax.set_yticks(yrange)
        self.ax.set_yticklabels(items)
                    
        # Set expert lines
        for i, (idx, item) in enumerate(zip(selected, items)):
            self.lines[item].set_data(assessments[idx], i)
            for j, quantile in enumerate(self.results.assessments.quantiles):
                self.markers[item][quantile].set_data(assessments[idx][j], i)
                    
        # self.figure.tight_layout()
        self.canvas.draw_idle()
            
            
    def update_item_plot(self):
        """
        Method to update the item plot after changes are made to the data selection.
        """
        # Set title
        self.set_title()

        if self.plottype == 'cdf':
            # Get item data
            lower, upper, assessments = self.get_item_data(full_dm_cdf=True)
        
            # Set expert lines
            quants = np.r_[0.0, self.results.assessments.quantiles, 1.0]
            for expert in self.results.experts.ids:
                row = assessments[expert]
                if row.ndim == 1:
                    self.lines[expert].set_data(np.r_[lower, row, upper], quants)
                else:
                    xdata, ydata = row.T
                    self.lines[expert].set_data(np.r_[lower, xdata, upper], np.r_[0.0, ydata, 1.0])

            # Format axis
            self.format_axis(lower, upper, 0, 1)
            self._set_data_visible()

        if self.plottype == 'exc prob':
            # Get item data
            lower, upper, assessments = self.get_item_data(full_dm_cdf=True)
        
            # Set expert lines
            quants = np.r_[0.0, self.results.assessments.quantiles, 1.0]
            for expert in self.results.experts.ids:
                row = assessments[expert]
                if row.ndim == 1:
                    self.lines[expert].set_data(np.r_[lower, row, upper], 1.0 - quants)
                else:
                    xdata, ydata = row.T
                    self.lines[expert].set_data(np.r_[lower, xdata, upper], 1.0 - np.r_[0.0, ydata, 1.0])

            # Format axis
            self.format_axis(lower, upper, 0, 1)
            self._set_data_visible()

        elif self.plottype == 'pdf':
            # Get item data
            lower, upper, assessments = self.get_item_data(full_dm_cdf=True)

            # Set expert lines
            maxdensity = 0
            for expert in self.results.experts.ids:
                row = assessments[expert]
                if row.ndim == 1:
                    binedges = np.r_[lower, row, upper]
                    xdata = np.repeat(binedges, 2)
                    pdensity = self.results.assessments.binprobs / (binedges[1:] - binedges[:-1])
                    ydata = np.r_[0, np.repeat(pdensity, 2), 0.0]
                else:
                    binedges, binprobs = row.T
                    xdata = np.repeat(binedges, 2)
                    binprobs = np.diff(binprobs)
                    pdensity = binprobs / (binedges[1:] - binedges[:-1])
                    ydata = np.r_[0, np.repeat(pdensity, 2), 0.0]

                self.lines[expert].set_data(xdata, ydata)
                maxdensity = max(maxdensity, max(pdensity))

            # Format axis
            self.format_axis(lower, upper, 0, 1.1 * maxdensity)
            self._set_data_visible()

        elif self.plottype == 'range':
            # Get item data
            lower, upper, assessments = self.get_item_data(full_dm_cdf=False)
                    
            selected = np.unique([idx.row() for idx in self.legend.selectedIndexes()])
            experts = [self.results.experts.ids[i] for i in selected]
            nexp = len(selected)
            yrange = list(range(nexp))

            # Format axis
            self.format_axis(lower, upper, -0.5, nexp-0.5)
            self.ax.set_yticks(yrange)
            self.ax.set_yticklabels(experts)
                        
            # Set expert lines
            for i, expert in enumerate(experts):
                self.lines[expert].set_data(assessments[expert], i)
                if expert in self.markers:
                    for j, quantile in enumerate(self.results.assessments.quantiles):
                        self.markers[expert][quantile].set_data(assessments[expert][j], i)
                        
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
            self.lines['realization'].set_visible(True)
            self.lines['realization'].set_xdata([value, value])
        else:
            self.lines['realization'].set_visible(False)

    def get_item_data(self, full_dm_cdf):
        """
        Get all the data to plot for a certain item
        """
        # Get item id
        itemid = self.item_cbox.combobox.currentIndex()
        
        # Get expert assessments and bounds for question
        assessments = {}
        for i, exp in enumerate(self.results.experts.ids):
            if i in self.results.experts.decision_makers and full_dm_cdf:
                assessments[exp] = self.results.assessments.full_cdf[exp][itemid]
                
            else:
                assessments[exp] = self.results.assessments.array[i, :, itemid]
            
        lower = self.results.lower_k[itemid]
        upper = self.results.upper_k[itemid]

        # Convert bounds form log scale to uniform scale in case of log background
        if self.results.items.scale[itemid] == 'log':
            lower = np.exp(lower)
            upper = np.exp(upper)

        return lower, upper, assessments

    def get_expert_data(self):
        """
        Get all the data to plot for a certain expert
        """
        # Get item id
        expertid = self.item_cbox.combobox.currentIndex()
        
        # Get expert assessments and bounds (no overshoot) for question
        assessments = self.results.assessments.array[expertid, :, :].T
        lower = self.results.lower
        upper = self.results.upper

        # Convert bounds form log scale to uniform scale in case of log background
        for i, scale in enumerate(self.results.items.scale):
            if scale == 'log':
                lower[i] = np.exp(lower[i])
                upper[i] = np.exp(upper[i])

        # Normalize data
        assessments = (assessments - lower[:, None]) / (upper - lower)[:, None]

        return assessments

    def format_axis(self, xmin, xmax, ymin, ymax):
        """
        Set axis limits, called after a plot has been changed.
        """
        # Get item id
        itemid = self.item_cbox.combobox.currentIndex()

        # Set x axis scale
        # if self.results.items.scale[itemid] == 'log':
        #     # self.ax.set_xscale('log')
        #     self.ax.set_xscale('linear')
        # else:
        #     self.ax.set_xscale('linear')

        # Set limits
        # self.ax.axis((xmin, xmax, ymin, ymax))
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)

    def set_title(self):
        """
        Set axis title, called after a plot has been changed.
        """
        if self.plotby == 'item':
            # Get item id
            itemid = self.item_cbox.combobox.currentIndex()
            # Add to label
            self.title.setText(self.results.items.questions[itemid])

        elif self.plotby == 'expert':
            # Get expert id
            expertid = self.item_cbox.combobox.currentIndex()
            # Add to label
            self.title.setText(self.results.experts.ids[expertid])

    def _set_data_visible(self):
        """
        Method to hide or show lines based on the selection in the legend table
        """
        # Get selected indices
        selected = [idx.row() for idx in self.legend.selectedIndexes()]
        
        # If plotting by item, show data for all experts
        if self.plotby == 'item':
            for i, expert in enumerate(self.results.experts.ids):
                self.lines[expert].set_visible(i in selected)
                if expert in self.markers:
                    for q in self.results.assessments.quantiles:
                        self.markers[expert][q].set_visible(i in selected)
        
        # If plotting by expert, show data for all items
        elif self.plotby == 'expert':
            for i, item in enumerate(self.results.items.ids):
                self.lines[item].set_visible(i in selected)
                for q in self.results.assessments.quantiles:
                    self.markers[item][q].set_visible(i in selected)
        
        # In case of a range plot, not only toggle visibility, but
        # also remove re-plot to remove 'invisible' items
        if self.plottype == 'range':
            self.update_plot()

        self.canvas.draw_idle()


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

        self.setWindowTitle('Information score per item')
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)

        self.setLayout(QtWidgets.QVBoxLayout())

        # Add checkbox for colors
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(QtWidgets.QLabel('Colormap:'))
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
            index_names=['Expert'],
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
        self.close_button = QtWidgets.QPushButton('Close')
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.close)

        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        button_box.addButton(self.close_button, QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(QtWidgets.QDialog.accept)

        self.layout().addWidget(button_box)

        self.resize(100 + 100 * min(len(results.experts.ids), 10), 600)

        self.arrmin = self.array.min()
        self.arrmax = self.array.max()

        self.cmap = cm.get_cmap('RdYlGn')

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
