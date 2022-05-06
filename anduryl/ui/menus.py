from PyQt5 import QtCore, QtWidgets

class TableMenu(QtWidgets.QMenu):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.tableheader = widget.table.horizontalHeader()
        self.headerlabels = [self.widget.model.headerData(i, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) for i in range(self.tableheader.count())]
        self.action_dict = {}

    def construct(self):
        
        # Add possibility to toggle column visibility
        self.addSeparator()
        show_columns_menu = self.addMenu("Show columns")
        self.action_dict["show_columns"] = {}
        for i, label in enumerate(self.headerlabels):
            action = show_columns_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(not self.tableheader.isSectionHidden(i))
            self.action_dict["show_columns"][label] = action

        # Add possibility to change font size
        # self.addSeparator()
        # self.action_dict['increase_font'] = self.addAction("Increase font size")
        # self.action_dict['decrease_font'] = self.addAction("Decrease font size")


    def perform_action(self, action):

         # Check if it is a show column action
        show_position = [i for i, show_action in self.action_dict["show_columns"].items() if action == show_action]
        if len(show_position) > 0:
            assert len(show_position) == 1
            i = self.headerlabels.index(show_position[0])
            self.tableheader.setSectionHidden(i, not self.tableheader.isSectionHidden(i))

        # elif action == self.action_dict["increase_font"]:
        #     font = self.widget.table.font()
        #     font.setPointSize(self.widget.table.font().pointSize() + 1)
        #     self.widget.table.setFont(font)
        
        # elif action == self.action_dict["decrease_font"]:
        #     font = self.widget.table.font()
        #     font.setPointSize(max(1, self.widget.table.font().pointSize() - 1))
        #     self.widget.table.setFont(font)
        


class ItemsContextMenu(TableMenu):
    def __init__(self, itemswidget, event):
        super().__init__(itemswidget)
        rownum = itemswidget.table.currentIndex().row()

        self.items = itemswidget.project.items
        self.itemswidget = itemswidget
        self.tableheader = self.itemswidget.table.horizontalHeader()

        self.construct(rownum)
        super().construct()

        self.perform_action(event, rownum)
        
    def construct(self, rownum):

        # Add actions
        self.action_dict["add_item"] = self.addAction("Add item")
        # Action to include or exclude an expert
        if rownum >= 0:
            excluded = self.items.ids[rownum] in self.items.excluded
            self.action_dict["exclude_item"] = self.addAction("Include this item" if excluded else "Exclude this item")
        # Remove item
        self.action_dict["remove_item"] = self.addAction("Remove item")
        self.addSeparator()
        # Actions to move items up or down
        self.action_dict["move_items"] = {}
        if rownum >= 0:
            move_items_menu = self.addMenu("Move item")
            # Add action to move item one position up or down
            self.action_dict["move_items"]["up"] = move_items_menu.addAction("Move item up")
            self.action_dict["move_items"]["down"] = move_items_menu.addAction("Move item down")
            move_items_menu.addSeparator()
            # Add actions to move item to a chosen position
            for i in range(len(self.items.ids)):
                if i == rownum:
                    continue
                self.action_dict["move_items"][i] = move_items_menu.addAction(f"Move item to row {i+1}")

        # Show assessments for item
        self.addSeparator()
        self.action_dict["show_assessments"] = self.addAction("Show item assessments")


    def perform_action(self, event, rownum):

        # Get action
        action = self.exec_(self.itemswidget.mapToGlobal(event.pos()))
        
        # Perform font size change and hide column actions
        super().perform_action(action)
        
        # Check if it is an item move action
        move_position = [i for i, move_action in self.action_dict["move_items"].items() if action == move_action]

        if action == self.action_dict["add_item"]:
            self.itemswidget.add_item()

        elif action == self.action_dict["remove_item"]:
            self.itemswidget.remove_item_clicked()

        elif len(move_position) > 0:
            assert len(move_position) == 1
            self.itemswidget.move_item_clicked(move_position[0])

        elif action == self.action_dict["show_assessments"]:
            rownum = self.itemswidget.table.currentIndex().row()
            self.itemswidget.mainwindow.assessmentswidget.table.setCurrentIndex(QtCore.QModelIndex())
            self.itemswidget.mainwindow.assessmentswidget.item_cbox.setCurrentIndex(rownum + 1)

        elif (rownum >= 0) and (action == self.action_dict["exclude_item"]):
            self.itemswidget.exclude_item_clicked()
        

class ExpertsContextMenu(TableMenu):
    def __init__(self, expertswidget, event):
        super().__init__(expertswidget)
        # Get current row
        rownum = expertswidget.table.currentIndex().row()

        self.experts = expertswidget.project.experts
        self.expertswidget = expertswidget
        self.tableheader = self.expertswidget.table.horizontalHeader()

        self.construct(rownum)
        super().construct()

        self.perform_action(event, rownum)

    def construct(self, rownum):

        decision_maker_selected = rownum in self.experts.decision_makers

        # Add actions
        self.action_dict["add_expert"] = self.addAction("Add an expert")

        if not decision_maker_selected and rownum >= 0:
            excluded = self.experts.ids[rownum] in self.experts.excluded
            self.action_dict["exclude_expert"] = self.addAction(
                "Include this expert" if excluded else "Exclude this expert  "
            )

        self.action_dict["remove_expert"] = self.addAction(
            "Remove decision maker" if decision_maker_selected else "Remove this expert"
        )
        self.addSeparator()
        self.action_dict["show_assessments"] = self.addAction(
            "Show DM assessments" if decision_maker_selected else "Show expert assessments"
        )

        if decision_maker_selected:
            self.action_dict["show_results"] = self.addAction("Show DM results")

    def perform_action(self, event, rownum):

        # get action
        action = self.exec_(self.expertswidget.mapToGlobal(event.pos()))

        # Perform font size change and hide column actions
        super().perform_action(action)
        
        decision_maker_selected = rownum in self.experts.decision_makers

        if action == self.action_dict["add_expert"]:
            self.expertswidget.add_expert()

        elif action == self.action_dict["remove_expert"]:
            self.expertswidget.remove_expert_clicked()

        elif action == self.action_dict["show_assessments"]:
            self.expertswidget.mainwindow.assessmentswidget.table.setCurrentIndex(QtCore.QModelIndex())
            self.expertswidget.mainwindow.assessmentswidget.expert_cbox.setCurrentIndex(rownum + 1)

        elif decision_maker_selected and action == self.action_dict["show_results"]:
            self.expertswidget.mainwindow.resultswidget.tabs.setCurrentIndex(
                self.experts.decision_makers.index(rownum)
            )

        elif not decision_maker_selected and (rownum >= 0) and action == self.action_dict["exclude_expert"]:
            self.exclude_expert_clicked()

class ApplyColorMenu(QtWidgets.QMenu):
    def __init__(self, legendtable, event):
        super().__init__()
        # Get current row
        rownum = legendtable.currentIndex().row()

        self.legendtable = legendtable

        self.action_dict = {}

        self.construct()

        self.perform_action(event, rownum)

    def construct(self):

        # Add actions
        self.action_dict["pick"] = self.addAction("Pick color")
        self.addSeparator()
        apply_color_menu = self.addMenu("Apply color to")

        self.action_dict["apply"] = {}
        self.action_dict["apply"]["All"] = apply_color_menu.addAction("All")
        for label in self.legendtable.labels:
            self.action_dict["apply"][label] = apply_color_menu.addAction(label)

    def perform_action(self, event, rownum):
        action = self.exec_(self.legendtable.mapToGlobal(event.pos()))
        if action == self.action_dict["pick"]:
            self.pick_color(rownum)

        # Check if it is a apply action
        apply_position = [label for label, apply_action in self.action_dict["apply"].items() if action == apply_action]
        if len(apply_position) > 0:
            assert len(apply_position) == 1
            label = apply_position[0]
            color = self.legendtable.item(rownum, 0).background().color()

            # Apply color to other rows
            if label == "All":
                for label in self.legendtable.labels:
                    self.legendtable.apply_color(color, label)
            else:
                self.legendtable.apply_color(color, label)

    def pick_color(self, row):
        # Choose color
        color = QtWidgets.QColorDialog.getColor()
        self.legendtable.apply_color(color, self.legendtable.labels[row])

    