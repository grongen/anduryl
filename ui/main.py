# -*- coding: utf-8 -*-
"""
Author      : Guus Rongen, TU Delft
"""

# import logging
import os
import subprocess
import sys
import traceback

import numpy as np
from PyQt5 import Qt, QtCore, QtGui, QtWidgets

from anduryl.ui.dialogs import NotificationDialog, get_icon

from anduryl.ui import widgets
from anduryl import io
from anduryl.ui.assessments import AssessmentsWidget
from anduryl.ui.experts import ExpertsWidget
from anduryl.ui.items import ItemsWidget
from anduryl.ui.results import ResultsWidget
from anduryl.core.main import Project



# logger = logging.getLogger(__name__)

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

# os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# mainfont = QtGui.QFont('Segoe UI')
# mainfont.setPixelSize(11)
# QtWidgets.QApplication.setFont(mainfont)

class MainWindow(QtWidgets.QMainWindow):
    """
    Main UI widget of Anduryl.
    """

    def __init__(self):
        """
        Constructer. Adds project and sets general settings.
        """
        super(MainWindow, self).__init__()

        self.appsettings = QtCore.QSettings("Anduryl")

        self.setAcceptDrops(True)

        self.setWindowTitle("Anduryl")

        # Add a project
        self.project = Project()

        self.profiling = False

        self.icon = get_icon()
        self.setWindowIcon(self.icon)

        self.setCursor(Qt.Qt.ArrowCursor)

        self.bordercolor = 'lightgrey'

        # Construct user interface
        self.init_ui()
        self.signals = Signals(self.project, self)

        def test_exception_hook(exctype, value, tback):
            """
            Function that catches errors and gives a Notification
            instead of a crashing application.
            """
            sys.__excepthook__(exctype, value, tback)
            self.setCursorNormal()
            NotificationDialog(
                text='\n'.join(traceback.format_exception_only(exctype, value)),
                severity='critical',
                details='\n'.join(traceback.format_tb(tback))
            )

        sys.excepthook = test_exception_hook

    def update_projectname(self, name=None):
        """
        Updates window title after a project has been loaded
        
        Parameters
        ----------
        name : str, optional
            Project name, by default None
        """
        if name is None:
            self.setWindowTitle("Anduryl [*]")
            self.appsettings.setValue('currentproject', '')
        else:
            self.setWindowTitle(f"Anduryl - {name} [*]")
            self.appsettings.setValue('currentproject', name)

    def dropEvent(self, e):
        """
        Function to open a project by drawin the file inside the UI.
        """
        fname = e.mimeData().text().replace('file:///', '')
        self.open_project(fname=fname)

    def dragEnterEvent(self, e):
        """
        Method to accept a dragged file, based on the extension.
        """
        if e.mimeData().hasText():
            if any(e.mimeData().text().endswith(ext) for ext in ['.rls', '.dtt', '.json']):
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()

    def setCursorWait(self):
        """
        Changes cursor to waiting cursor.
        """
        Qt.QApplication.setOverrideCursor(Qt.QCursor(QtCore.Qt.WaitCursor))
        Qt.QApplication.processEvents()

    def setCursorNormal(self):
        """
        Changes cursor (back) to normal cursor.
        """
        Qt.QApplication.restoreOverrideCursor()

    def init_ui(self):
        """
        Construct UI, by splitting the main window and adding the
        different widgets with tables.
        """
        mainsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.setCentralWidget(mainsplitter)

        # Expert table
        self.expertswidget = ExpertsWidget(self)

        # Items table
        self.itemswidget = ItemsWidget(self)
        leftsplitter = widgets.LogoSplitter(self.expertswidget, self.itemswidget, 'Experts', 'Items')
        leftsplitter.setSizes([100, 200])

        # Items table
        self.assessmentswidget = AssessmentsWidget(self)
        self.resultswidget = ResultsWidget(self)

        self.rightsplitter = widgets.LogoSplitter(self.assessmentswidget, self.resultswidget, 'Assessments', 'Results')
        self.rightsplitter.setSizes([200, 0])

        mainsplitter.addWidget(leftsplitter)
        mainsplitter.addWidget(self.rightsplitter)
        mainsplitter.setSizes([550, 550])

        self.init_menubar()

        mainsplitter.setStyleSheet( "QSplitter::handle{background:white}")
        self.rightsplitter.setStyleSheet("QSplitter::handle{background:white}")
        leftsplitter.setStyleSheet( "QSplitter::handle{background:white}")

        self.setGeometry(400, 200, 1100, 700)

        self.show()

    def getIcon(self, iconname):
        """
        Retrieve icon from data dir and set to GUI
        
        Parameters
        ----------
        iconname : str
            File name of the icon
        
        Returns
        -------
        QtGui.QIcon
            Qt object of icon
        """
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle, the pyInstaller bootloader
            # extends the sys module by a flag frozen=True and sets the app
            # path into variable _MEIPASS'.
            application_path = sys._MEIPASS
            datadir = os.path.join(application_path, 'data')

        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            datadir = os.path.join(application_path, '..', 'data')

        iconpath = os.path.join(datadir, iconname)
        if not os.path.exists(iconpath):
            raise OSError('Icon in path: "{}" not found'.format(iconpath))

        return QtGui.QIcon(iconpath)

    def init_menubar(self):
        """
        Constructs the menu bar.
        """

        menubar = self.menuBar()

        new_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon), 'New', self)
        new_action.setShortcut(QtGui.QKeySequence.New)
        new_action.setStatusTip('Create a new project')
        new_action.triggered.connect(self.new_project)

        openAction = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), 'Open', self)
        openAction.setStatusTip('Open project')
        openAction.setShortcut(QtGui.QKeySequence.Open)
        openAction.triggered.connect(self.open_project)

        saveAction = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton), 'Save', self)
        saveAction.setStatusTip('Save project')
        saveAction.setShortcut(QtGui.QKeySequence.Save)
        saveAction.triggered.connect(self.save_project)

        saveAsAction = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton), 'Save as', self)
        saveAsAction.setStatusTip('Save project as...')
        saveAsAction.setShortcut('Ctrl+Shift+S')
        saveAsAction.triggered.connect(self.save_project_as)

        exitAction = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Close Anduryl')
        exitAction.triggered.connect(self.close)

        file_menu = menubar.addMenu('&File')
        file_menu.addAction(new_action)
        file_menu.addAction(openAction)
        file_menu.addSeparator()
        file_menu.addAction(saveAction)
        file_menu.addAction(saveAsAction)
        file_menu.addSeparator()
        file_menu.addAction(exitAction)

        file_menu = menubar.addMenu('&Experts')

        add_expert_action = QtWidgets.QAction(QtGui.QIcon(), 'Add an expert', self)
        add_expert_action.setStatusTip('Add an expert to the project.')
        add_expert_action.triggered.connect(self.expertswidget.add_expert)
        file_menu.addAction(add_expert_action)

        remove_expert_action = QtWidgets.QAction(QtGui.QIcon(), 'Remove selected expert', self)
        remove_expert_action.setStatusTip('Remove an expert from the project.')
        remove_expert_action.triggered.connect(self.expertswidget.remove_expert_clicked)
        file_menu.addAction(remove_expert_action)

        file_menu = menubar.addMenu('&Item')

        add_item_action = QtWidgets.QAction(QtGui.QIcon(), 'Add item', self)
        add_item_action.setStatusTip('Add an item to the project.')
        add_item_action.triggered.connect(self.itemswidget.add_item)
        file_menu.addAction(add_item_action)

        remove_item_action = QtWidgets.QAction(QtGui.QIcon(), 'Remove selected item', self)
        remove_item_action.setStatusTip('Remove an item from the project.')
        remove_item_action.triggered.connect(self.itemswidget.remove_item)
        file_menu.addAction(remove_item_action)

        quantile_action = QtWidgets.QAction(QtGui.QIcon(), '&Quantiles', self)
        quantile_action.setStatusTip('Change quantiles')
        quantile_action.triggered.connect(self.assessmentswidget.change_quantiles)
        file_menu = menubar.addAction(quantile_action)

        calculate_action = QtWidgets.QAction(QtGui.QIcon(), '&Calculate', self)
        calculate_action.setStatusTip('Calculate decision maker or robustness table')
        calculate_action.triggered.connect(self.expertswidget.add_decision_maker)
        file_menu = menubar.addAction(calculate_action)

        export_menu = menubar.addMenu('&Export')
        for overview in ['experts', 'items', 'assessments']:
            export_action = QtWidgets.QAction(QtGui.QIcon(), overview.capitalize(), self)
            export_action.setStatusTip(f'{overview.capitalize()}')
            export_action.triggered.connect(getattr(self, f'{overview}widget').to_csv)
            export_menu.addAction(export_action)

        self.result_menu = export_menu.addMenu('Results')
        self.result_menu.setEnabled(False)
        self.subresultsmenu = {}

        help_menu = menubar.addMenu('&Help')
        doc_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView), 'Documentation', self)
        doc_action.setStatusTip('Open Anduryl documentation')
        doc_action.triggered.connect(self.open_documentation)
        help_menu.addAction(doc_action)

    def open_documentation(self):

        if getattr(sys, 'frozen', False):
            application_path = sys._MEIPASS
            indexpath = os.path.join('"'+application_path+'"', 'doc', 'index.html')

        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            indexpath = os.path.join('"'+application_path+'"', '..', 'doc', 'build', 'html', 'index.html')
        
        # Open index html
        subprocess.Popen(indexpath, shell=True)

    def add_export_actions(self, resultsoverview):
        """
        Method to add expert action when new results have been calculated.
        In the 'export' menu the result button is enabled, and export
        options for the new results are added.
        
        Parameters
        ----------
        resultsoverview : ResultOverview class
            Object with the results for a calculated decision maker
        """

        dm_id = resultsoverview.settings['id']

        self.subresultsmenu[dm_id] = self.result_menu.addMenu(dm_id)
        self.result_menu.setEnabled(True)
        
        # Add export Expert scores
        export_scores_action = QtWidgets.QAction(QtGui.QIcon(), 'Expert scores', self)
        export_scores_action.triggered.connect(lambda: io.table_to_csv(resultsoverview.scores_model, self))
        self.subresultsmenu[dm_id].addAction(export_scores_action)

        # Add export robustness
        for key in ['Items', 'Experts']:
            if key in resultsoverview.robustness_model:
                robustness_action = QtWidgets.QAction(QtGui.QIcon(), f'Robustness per {key[:-1].lower()}', self)
                robustness_action.triggered.connect(lambda: io.table_to_csv(resultsoverview.robustness_model[key], self))
                self.subresultsmenu[dm_id].addAction(robustness_action)

        # Add export Expert CDF
        def export_cdf():
            """
            Function to expert a decision makers CDF.
            """
            items = resultsoverview.results.items.ids
            cdfs = resultsoverview.results.assessments.full_cdf[dm_id]
            index = np.concatenate([[item] * len(cdfs[i]) for i, item in enumerate(items)], axis=-1)
            data = np.vstack([cdfs[i] for i in range(len(items))])

            options = QtWidgets.QFileDialog.Options() | QtWidgets.QFileDialog.DontUseNativeDialog
            # Set current dir
            currentdir = self.appsettings.value('currentdir', '.', type=str)
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Anduryl - Save as CSV', '.', "CSV (*.csv)", options=options)
            if not path:
                return None

            with open(path, 'w') as f:
                text = 'ItemId;Value;P(X<x)\n' + '\n'.join([f'{idx};{vals[0]};{vals[1]}' for idx, vals in zip(index, data)])
                f.write(text)
                
        export_cdf_action = QtWidgets.QAction(QtGui.QIcon(), 'DM CDF', self)
        export_cdf_action.triggered.connect(export_cdf)
        self.subresultsmenu[dm_id].addAction(export_cdf_action)

    def remove_export_actions(self, dm_id):
        """
        Method to remove the export actions from the menu after the results
        are deleted.
        
        Parameters
        ----------
        dm_id : str
            ID of the decision maker to remove.
        """
        # TODO: remove actions too
        self.subresultsmenu[dm_id].deleteLater()
        del self.subresultsmenu[dm_id]

        # Disable results menu after all results have been removed
        if len(self.subresultsmenu) == 0:
            self.result_menu.setEnabled(False)

    def closeEvent(self, event):
        """
        Method called when application is closed. The method checks
        whether there are unsaved changes, and ask the user to save,
        discard or cancel.
        """
        reply = self.ok_to_continue('Close project')
        if reply == QtWidgets.QMessageBox.Cancel:
            event.ignore()
            return None
        if reply == QtWidgets.QMessageBox.Save:
            self.save_project()
        if self.profiling:
            self.end_profiling()
        event.accept()
        
    def start_profiling(self):
        """
        Start profiling the code performance.
        """
        import cProfile
        self.profiling = True
        self.pr = cProfile.Profile()
        self.pr.enable()

    def end_profiling(self):
        """
        End profiling the code performance, and write the
        results to a file.
        """
        from io import StringIO
        import pstats
        self.pr.disable()
        s = StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(self.pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        with open('profile.txt', 'w') as f:
            f.write(s.getvalue())

    def get_project_file(self):
        """
        Opens a dialog to select a project file to open.
        """
        # Set open file dialog settings
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog

        # Set current dir
        currentdir = self.appsettings.value('currentdir', '.', type=str)

        # Open dialog to select file
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Anduryl - Open project', currentdir, "All data files (*.json *.dtt);;JSON (*.json);;Excalibar (*.dtt)", options=options)

        return fname

    def ok_to_continue(self, title):
        """
        Asks the user whether results should be saved, discarded or the action cancelled.
        """
        if self.isWindowModified():
            currentproject = self.appsettings.value('currentproject', '', type=str)
            return QtWidgets.QMessageBox.question(
                self,
                f"Anduryl - {title}",
                f"Do you want to save changes you made to \"{currentproject}\"?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel
            )

        else:
            return QtWidgets.QMessageBox.Discard

    def save_project_as(self, fname=None):
        """
        Asks the user for the file name to save the project to.
        If the file name is passed, the user is not asked the file
        and the project is saved directly.
        
        Parameters
        ----------
        fname : str, optional
            File name, by default None
        """

        # if fname is None:
        # Set open file dialog settings
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtWidgets.QFileDialog.DontConfirmOverwrite

        # Set current dir
        currentdir = self.appsettings.value('currentdir', '.', type=str)

        # Open dialog to select file
        fname, ext = QtWidgets.QFileDialog.getSaveFileName(self, 'Anduryl - Save project', currentdir, "JSON (*.json);;Excalibar (*.dtt)", options=options)

        if fname == "":
            return None

        # Add extension if not given in file
        for end in ['.dtt', '.json']:
            if end in ext and not fname.endswith(end):
                fname += end

        if os.path.exists(fname):
            reply = QtWidgets.QMessageBox.warning(
                self,
                "Anduryl - Save project",
                f"{os.path.split(fname)[-1]} already exists.\nDo you want to overwrite it?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return None

        if '.dtt' in ext:
            # Check lengths of ids
            if max([len(exp_id) for exp_id in self.project.experts.ids]) > 8:
                NotificationDialog('Some expert id\'s are longer than 8 characters. They will be shortened to 8 characters for compatibility with Excalibur. Check if the id\'s are still unique.')
            if  max([len(item_id) for item_id in self.project.items.ids]) > 14:
                NotificationDialog('Some item id\'s are longer than 14 characters. They will be shortened to 14 characters for compatibility with Excalibur. Check if the id\'s are still unique.')

        # Save files
        self.update_projectname(os.path.basename(fname))

        self.project.io.to_file(fname)
        self.setWindowModified(False)

    def save_project(self):
        """
        Save current project, checks if the file name is already known.
        If not, the save as function is called and the user is asked to
        pick a file.
        """

        # If no current project, save as...
        currentproject = self.appsettings.value('currentproject', '', type=str)
        if currentproject == '':
            self.save_project_as()

        else:
            # Get current directory
            currentdir = self.appsettings.value('currentdir', '.', type=str)

            # Else, save files directly
            self.project.io.to_file(os.path.join(currentdir, currentproject))
            self.setWindowModified(False)


    def open_project(self, *args, fname=None):
        """
        Method that loads project file and builds gui
        """

        if fname is None:
            fname = self.get_project_file()
            if fname == "":
                return None

        # Open project
        self.signals._about_to_be_changed()
        self.new_project()
        self.setCursorWait()

        # Load from file
        self.project.io.load_file(fname)

        # Add results if loaded from json
        # TODO: if adding this feature, make sure results are removed (cleared) before being added
        # if any(self.project.results):
            # for _, results in self.project.results.items():
                # self.resultswidget.add_results(results.settings)
            # Move splitter if results are hidden
            # if self.rightsplitter.sizes()[-1] == 0:
                # self.rightsplitter.setSizes([200, 400])

        self.signals.update_gui()
        self.signals.update_color_range()
        self.signals._changed()

        # save current dir
        self.appsettings.setValue('currentdir', os.path.dirname(fname))
        self.update_projectname(os.path.basename(fname))
        self.setCursorNormal()

    def new_project(self):
        """
        Opens a new projcet. Checks if results should be saved. All
        items, experts and results are removed.
        """

        # Check if a project is already open
        if any(self.project.experts.ids) or any(self.project.items.ids):
            reply = self.ok_to_continue('New project')
            if reply == QtWidgets.QMessageBox.Cancel:
                return None
            elif reply == QtWidgets.QMessageBox.Save:
                self.save_project()

        self.setCursorWait()
        # Remove all experts
        for i in reversed(range(len(self.project.experts.ids))):
            # If decision maker, also close the results tab
            if i in self.project.experts.decision_makers:
                self.resultswidget.close_results(index=None, expert=self.project.experts.ids[i])
            self.expertswidget.remove_expert(self.project.experts.ids[i])

        # Remove all items
        for i in reversed(range(len(self.project.items.ids))):
            self.itemswidget.remove_item(self.project.items.ids[i])

        # Reset percentiles
        self.assessmentswidget.change_quantiles(newquantiles=[0.05, 0.5, 0.95])

        # Update UI
        self.update_projectname()
        self.signals.update_gui()
        self.setCursorNormal()


class Signals:
    """Signal class. Contains all signals that are called
    to update the GUI after changes.
    """

    def __init__(self, project, main):
        """Constructor

        Parameters
        ----------
        project : Project class
            Project class, is used for all the references to other objects
        """
        self.project = project
        self.main = main

    def update_color_range(self):
        """
        Updates the bounds of the arrays and colormaps
        """
        self._about_to_be_changed()
        self.main.assessmentswidget.model.update_range()
        self.main.assessmentswidget.update_label()
        self._changed()

    def selection_changes(self):
        """
        Updates selection of array that is shown in table
        """
        self._about_to_be_changed()
        self.main.assessmentswidget.model.selector.update()
        self._changed()

    def _about_to_be_changed(self):
        """
        Signal that the table views are about to be changed
        """
        self.main.expertswidget.model.layoutAboutToBeChanged.emit()
        self.main.itemswidget.model.layoutAboutToBeChanged.emit()
        self.main.assessmentswidget.model.layoutAboutToBeChanged.emit()

    def _changed(self):
        """
        Signal that the table views are changed
        """
        self.main.expertswidget.model.layoutChanged.emit()
        self.main.itemswidget.model.layoutChanged.emit()
        self.main.assessmentswidget.model.layoutChanged.emit()

    def update_gui(self):
        """
        Updates:
        - Tables (refresh view)
        - Comboboxes
        """
        self._about_to_be_changed()
        # Update combobox items
        self.main.assessmentswidget.update_comboboxes()

        # Updates dataselection
        expidx = self.main.assessmentswidget.expert_cbox.currentIndex()
        itemidx = self.main.assessmentswidget.item_cbox.currentIndex() 
        if expidx != 0:
            self.main.assessmentswidget.model.selector.update(dim=0, index=expidx-1)
        elif itemidx != 0:
            self.main.assessmentswidget.model.selector.update(dim=2, index=itemidx-1)
        else:
            self.main.assessmentswidget.model.selector.update()
        
        
        self._changed()

    def update_headers(self):
        """
        Updates:
        - Tables (refresh view)
        - Comboboxes
        """
        self._about_to_be_changed()
        table = self.main.assessmentswidget.table
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for i in range(2):
            table.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.Fixed)
            table.setColumnWidth(i, 100)

        self._changed()

    def update_ids(self):
        """
        Updates the combobox id's
        """
        self._about_to_be_changed()
        # Update combobox items
        self.main.assessmentswidget.change_combobox_ids()

        self._changed()
