import numpy as np
from PyQt5 import Qt, QtCore, QtGui, QtWidgets

from anduryl import io
from anduryl.ui import widgets
from anduryl.ui.dialogs import NotificationDialog
from anduryl.ui.models import ItemDelegate, ItemsListsModel, ItemsBoundsModel


class ItemsWidget(QtWidgets.QFrame):
    """
    Widget with the items table
    """

    def __init__(self, mainwindow):

        super(ItemsWidget, self).__init__()

        self.mainwindow = mainwindow
        self.project = mainwindow.project
        self.construct_widget()

    def construct_widget(self):
        """
        Construct the UI widget
        """
        # Create the table view
        self.table = QtWidgets.QTableView()
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableView{border: 1px solid " + self.mainwindow.bordercolor + "}")
        self.table.installEventFilter(self)

        # Create and add model
        self.model = ItemsListsModel(parentwidget=self)
        self.model.leftalign.append(3)

        self.table.setModel(self.model)
        self.table.setItemDelegate(ItemDelegate(self.model))

        for i in range(3):
            self.table.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        mainbox = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Items")
        label.setContentsMargins(5, 2.5, 5, 2.5)
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
                text = io.selection_to_text(selection)
                QtWidgets.qApp.clipboard().setText(text)
                return True
        return self.mainwindow.eventFilter(source, event)

    def to_csv(self):
        """
        Calls the anduryl.io.table_to_csv function for the table model
        """
        io.table_to_csv(self.model, self.mainwindow)

    def add_item(self):
        """
        Add item button clicked. Adds an item to the project and updates the UI accordingly
        """

        # Add expert
        self.project.items.add_item(item_id=f"item{len(self.project.items.ids):02d}")

        # Update GUI
        self.mainwindow.signals.update_gui()
        self.mainwindow.signals.update_color_range()
        self.mainwindow.setWindowModified(True)

    def move_item_clicked(self, newpos):
        """
        Function that checks whether an item is selected
        when the option "move item [position]" is clicked.
        """
        rownum = self.table.currentIndex().row()
        if rownum == -1:
            NotificationDialog("Select a row to move an item")
            return None
        # Get item id
        itemid = self.project.items.ids[rownum]

        # Remove expert from table widget
        if newpos == "up":
            newpos = max(rownum - 1, 0)
        elif newpos == "down":
            newpos = min(rownum + 1, len(self.project.items.ids) - 1)

        self.move_item(itemid, newpos)

    def move_item(self, itemid, newpos):
        """
        Moves an item within the project and updates the UI accordingly.

        Parameters
        ----------
        itemid : str
            Item id
        """
        # Remove from project
        self.project.items.move_item(item_id=itemid, newpos=newpos)
        self.mainwindow.assessmentswidget.table.setCurrentIndex(QtCore.QModelIndex())
        self.mainwindow.signals.update_gui()
        self.mainwindow.signals.update_color_range()
        self.table.setCurrentIndex(QtCore.QModelIndex())
        self.mainwindow.setWindowModified(True)

    def remove_item_clicked(self):
        """
        Function that checks whether an item is selected
        when the option "remove item" is clicked.
        """
        rownum = self.table.currentIndex().row()
        if rownum == -1:
            NotificationDialog("Select a row to remove an item")
            return None
        # Get item id
        itemid = self.project.items.ids[rownum]

        # Remove expert from table widget
        self.remove_item(itemid)

    def remove_item(self, itemid):
        """
        Removes an item form the project and updates the UI accordingly.

        Parameters
        ----------
        itemid : str
            Item id
        """
        # Remove from project
        self.project.items.remove_item(item_id=itemid)
        self.mainwindow.assessmentswidget.table.setCurrentIndex(QtCore.QModelIndex())
        self.mainwindow.signals.update_gui()
        self.mainwindow.signals.update_color_range()
        self.table.setCurrentIndex(QtCore.QModelIndex())
        self.mainwindow.setWindowModified(True)

    def toggle_item(self, item):
        """
        Executed when the checkbox before an item is clicked. The item is
        added or removed to the excluded list of the items class.

        Parameters
        ----------
        item : str
            Item id
        """
        if item in self.project.items.excluded:
            self.project.items.excluded.remove(item)
        else:
            self.project.items.excluded.append(item)

    def exclude_item_clicked(self):
        """
        Function that checks whether an item is selected
        when the option "exclude item" is clicked.
        """
        rownum = self.table.currentIndex().row()
        if rownum == -1:
            NotificationDialog("Select a row to exclude an item")
            return None

        # Remove expert from table widget
        self.toggle_item(self.project.items.ids[rownum])

    def contextMenuEvent(self, event):
        """
        Describes the context menu for the items widget, and
        handles the clicked action
        """

        menu = QtWidgets.QMenu(self)
        rownum = self.table.currentIndex().row()

        # Add actions
        add_item_action = menu.addAction("Add item")
        # Action to include or exclude an expert
        if rownum >= 0:
            excluded = self.project.items.ids[rownum] in self.project.items.excluded
            exclude_item_action = menu.addAction("Include this item" if excluded else "Exclude this item")
        # Remove item
        remove_item_action = menu.addAction("Remove item")
        menu.addSeparator()
        # Actions to move items up or down
        move_items_actions = {}
        if rownum >= 0:
            move_items_menu = menu.addMenu("Move item")
            # Add action to move item one position up or down
            move_items_actions["up"] = move_items_menu.addAction("Move item up")
            move_items_actions["down"] = move_items_menu.addAction("Move item down")
            move_items_menu.addSeparator()
            # Add actions to move item to a chosen position
            for i in range(len(self.project.items.ids)):
                if i == rownum:
                    continue
                move_items_actions[i] = move_items_menu.addAction(f"Move item to row {i+1}")

        # Show assessments for item
        menu.addSeparator()
        show_assessments_action = menu.addAction("Show item assessments")

        # Get action
        action = menu.exec_(self.mapToGlobal(event.pos()))
        # Check if it is an item move action
        move_position = [i for i, move_action in move_items_actions.items() if action == move_action]

        if action == add_item_action:
            self.add_item()

        elif action == remove_item_action:
            self.remove_item_clicked()

        elif len(move_position) > 0:
            assert len(move_position) == 1
            self.move_item_clicked(move_position[0])

        elif action == show_assessments_action:
            rownum = self.table.currentIndex().row()
            self.mainwindow.assessmentswidget.table.setCurrentIndex(QtCore.QModelIndex())
            self.mainwindow.assessmentswidget.item_cbox.setCurrentIndex(rownum + 1)

        elif (rownum >= 0) and (action == exclude_item_action):
            self.exclude_item_clicked()

    def set_bounds(self, event):
        # Open dialog to set bounds
        self.item_bounds_dialog = ItemBoundsDialog(self)
        self.item_bounds_dialog.exec_()


class CheckboxDelegate(QtWidgets.QItemDelegate):
    """
    A delegate that places a fully functioning QPushButton in every
    cell of the column to which it's applied
    """

    def __init__(self, parent):
        # The parent is not an optional argument for the delegate as
        # we need to reference it in the paint method (see below)
        super(QtWidgets.QItemDelegate, self).__init__()
        self.tableview = parent

    def paint(self, painter, option, index):
        # This method will be called every time a particular cell is
        # in view and that view is changed in some way.  We ask the
        # delegates parent (in this case a table view) if the index
        # in question (the table cell) already has a widget associated
        # with it.  If not, create one with the text for this index and
        # connect its clicked signal to a slot in the parent view so
        # we are notified when its used and can do something.
        if not self.tableview.indexWidget(index):

            cell_widget = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(cell_widget)
            checkbox = QtWidgets.QCheckBox()
            # if self.model.lists[col][row]:
            # checkbox.setChecked(True)
            layout.addWidget(checkbox)
            layout.setAlignment(QtCore.Qt.AlignHCenter)

            self.tableview.setIndexWidget(index, cell_widget)


class CustomTableView(QtWidgets.QTableView):
    def __init__(self, parent):
        self.parent = parent
        super(QtWidgets.QTableView, self).__init__()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.parent.update_checkbox(self.currentIndex())
        super(QtWidgets.QTableView, self).keyPressEvent(event)


class ItemBoundsDialog(QtWidgets.QDialog):
    """
    Dialog to get parameters for calculating decision maker
    """

    def __init__(self, parentwidget):
        """
        Constructor
        """
        super(ItemBoundsDialog, self).__init__()

        self.setWindowTitle("Set bounds per item")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)

        self.setLayout(QtWidgets.QVBoxLayout())
        hlayout = QtWidgets.QHBoxLayout()

        # Create the table view
        self.table = CustomTableView(self)
        self.table.verticalHeader().setVisible(True)
        # self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        # # Create and add model
        self.model = ItemsBoundsModel(parentwidget=parentwidget)

        self.table.setModel(self.model)

        # for col in np.where(self.model.checkable)[0]:
        # delegate = CheckboxDelegate(self.table)
        # self.table.setItemDelegateForColumn(5, delegate)
        # print(id(delegate))
        # delegate = CheckboxDelegate(self.table)
        # self.table.setItemDelegateForColumn(6, delegate)
        # print(id(delegate))
        # self.table.setItemDelegate(ButtonDelegate(self.table))
        # self.table.setItemDelegateForColumn(6, ButtonDelegate(self.table))
        # self.table.setItemDelegateForColumn(7, ButtonDelegate(self.table))

        # Now we change the cells for the chechbox columns for checkboxes
        for col in np.where(self.model.checkable)[0]:
            for row in range(self.model.rowCount()):
                cell_widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout(cell_widget)
                c = QtWidgets.QCheckBox()
                if self.model.lists[col][row]:
                    c.setChecked(True)
                layout.addWidget(c)
                layout.setAlignment(QtCore.Qt.AlignHCenter)
                self.table.setIndexWidget(self.model.index(row, col), cell_widget)

        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for i in np.where(np.array(self.model.checkable))[0]:
            self.table.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.Fixed)
            self.table.setColumnWidth(i, 20)

        self.layout().addWidget(self.table)

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

        self.resize(600, 400)

    def update_checkbox(self, index):
        checkbox = self.table.indexWidget(index).children()[1]
        checkbox.setChecked(bool(abs(checkbox.isChecked() - 1)))

    def process_checkboxes(self):
        for col in np.where(self.model.checkable)[0]:
            for row in range(self.model.rowCount()):
                checkbox = self.table.indexWidget(self.model.index(row, col)).children()[1]
                self.model.lists[col][row] = checkbox.isChecked()

    def close(self):
        self.process_checkboxes()
        super().close()


# class CustomTableWidget(QtWidgets.QTableWidget):

#     def __init__(self, dct, idkey, checkboxindex=None):
#         super(CustomTableWidget, self).__init__()

#         self.setRowCount(len(dct[idkey]))
#         self.setColumnCount(len(dct) - 1)

#         # Set index and column labels
#         self.idkey = idkey
#         self.setVerticalHeaderLabels(dct[idkey])
#         self.columns = list(dct.keys())
#         self.columns.remove(idkey)
#         self.setHorizontalHeaderLabels(self.columns)

#         # Format
#         self.setShowGrid(False)
#         self.setAlternatingRowColors(True)

#         # Add data
#         self.set_data(dct, checkboxindex)

#     def set_data(self, dct, checkboxindex):
#         for key, values in dct.items():
#             if key == self.idkey:
#                 continue
#             # Get column number
#             colnum = self.columns.index(key)
#             if key in checkboxindex:
#                 for i, val in enumerate(values):
#                     cell_widget = QtWidgets.QTableWidgetItem()
#                     # layout = QtWidgets.QHBoxLayout()
#                     # c = QtWidgets.QCheckBox()
#                     # c.setChecked(bool(val))
#                     # layout.addWidget(c)
#                     # layout.setAlignment(QtCore.Qt.AlignHCenter)
#                     # cell_widget.setLayout(layout)
#                     self.setItem(i, colnum, cell_widget)
#             else:
#                 for i, val in enumerate(values):
#                     self.setItem(i, colnum, QtWidgets.QTableWidgetItem(f'{val:.4g}'))


# class ItemBoundsDialog(QtWidgets.QDialog):
#     """
#     Dialog to get parameters for calculating decision maker
#     """
#     def __init__(self, parentwidget):
#         """
#         Constructor
#         """
#         super(ItemBoundsDialog, self).__init__()

#         self.setWindowTitle('Set bounds per item')
#         self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)

#         self.setLayout(QtWidgets.QVBoxLayout())

#         # Create the table view
#         project = parentwidget.mainwindow.project

#         quantiles = project.assessments.quantiles

#         tabledata = {
#             'IDS': project.items.ids,
#             'Lower bound': project.items.item_bounds[:, 0],
#             'Upper bound': project.items.item_bounds[:, 1],
#             'Lower overshoot': project.items.item_bounds[:, 0],
#             'Upper overshoot': project.items.item_bounds[:, 1]
#         }
#         for i in range(len(quantiles)):
#             tabledata[f'{quantiles[i]:.4g}'] = project.items.use_quantiles[:, i]

#         self.table = CustomTableWidget(tabledata, 'IDS', checkboxindex=[f'{q:.4g}' for q in quantiles])


#         # project.items.item_bounds[i, col]

#         # # Now we change the cells for the chechbox columns for checkboxes
#         # for col in np.where(self.model.checkable)[0]:
#         #     for row in range(self.model.rowCount()):
#         #         cell_widget = QtWidgets.QWidget()
#         #         layout = QtWidgets.QHBoxLayout(cell_widget)
#         #         c = QtWidgets.QCheckBox()
#         #         if self.model.lists[col][row]:
#         #             c.setChecked(True)
#         #         layout.addWidget(c)
#         #         layout.setAlignment(QtCore.Qt.AlignHCenter)
#         #         self.table.setIndexWidget(self.model.index(row, col), cell_widget)

#         # self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
#         # for i in range(3):
#         #     self.table.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.Fixed)
#         #     self.table.setColumnWidth(i, 100)

#         self.layout().addWidget(self.table)

#         # Add close button
#         self.layout().addWidget(widgets.HLine())

#         # OK and Cancel buttons
#         self.close_button = QtWidgets.QPushButton('Close')
#         self.close_button.setAutoDefault(False)
#         self.close_button.clicked.connect(self.close)

#         button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
#         button_box.addButton(self.close_button, QtWidgets.QDialogButtonBox.RejectRole)
#         button_box.accepted.connect(QtWidgets.QDialog.accept)

#         self.layout().addWidget(button_box)

#         self.resize(600, 600)

#     # def update_checkbox(self, index):
#     #     checkbox = self.table.indexWidget(index).children()[1]
#     #     checkbox.setChecked(bool(abs(checkbox.isChecked()-1)))

#     # def process_checkboxes(self):
#     #     for col in np.where(self.model.checkable)[0]:
#     #         for row in range(self.model.rowCount()):
#     #             checkbox = self.table.indexWidget(self.model.index(row, col)).children()[1]
#     #             self.model.lists[col][row] = checkbox.isChecked()

#     # def close(self):
#     #     self.process_checkboxes()
#     #     super().close()
