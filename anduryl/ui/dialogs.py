import os
import sys
from PyQt5 import QtGui, QtWidgets, QtCore
from anduryl.ui import widgets
from pathlib import Path


def get_icon():
    # In case of PyInstaller exe
    if getattr(sys, "frozen", False):
        application_path = sys._MEIPASS
        iconpath = os.path.join(application_path, "data", "icon.ico")
    # In case of regular python
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        iconpath = os.path.join(application_path, "..", "data", "icon.ico")

    return QtGui.QIcon(iconpath)


class NotificationDialog(QtWidgets.QMessageBox):
    """
    Custom notification dialog
    """

    def __init__(self, text, severity="information", details=""):
        """
        Create a notification dialog with a given text, severity level
        and if needed some details.

        Parameters
        ----------
        text : str
            Message text
        severity : str, optional
            Severity level, warning, critical or information (default)
        details : str, optional
            Optional details, by default ''
        """

        super().__init__()

        self.setText(text)

        if severity == "warning":
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
            self.setWindowTitle("Warning")
        elif severity == "critical":
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
            self.setWindowTitle("Critical")
        elif severity == "information":
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)
            self.setWindowTitle("Notification")

        self.setIconPixmap(icon.pixmap(icon.actualSize(QtCore.QSize(36, 36))))

        self.setWindowIcon(get_icon())

        if details:
            self.setDetailedText("Details:\n{}".format(details))

        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.resize(200, 400)

        self.exec_()

    def resizeEvent(self, event):
        """
        Method called when the details are opened, and the window is enlarged.
        """

        result = super(NotificationDialog, self).resizeEvent(event)

        details_box = self.findChild(QtWidgets.QTextEdit)
        # 'is not' is better style than '!=' for None
        if details_box is not None:
            details_box.setFixedSize(500, 250)

        return result


class ImportCSVDialog(QtWidgets.QDialog):
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
        super(ImportCSVDialog, self).__init__()

        # Pointer to results and settings from ResultsOverview
        self.icon = parent.icon
        self.appsettings = parent.appsettings
        self.construct_dialog()

    def construct_dialog(self):
        """
        Constructs the widget.
        """
        self.setWindowTitle("Anduryl - Import CSV")
        self.setWindowIcon(self.icon)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        # CSV line edit
        width = widgets.get_width("Seperator:")
        self.assessments_label = QtWidgets.QLabel(
            """Give the csv with assessment. The file should contain:
    - a column with expert ids called "ExpertID"
    - a column with item ids called "ItemID". Each ItemID should be present in the second CSV as well.
    - one column for each elicited quantile ([0 - 1], in ascending order)"""
        )
        self.assessments_csv = widgets.ExtendedLineEdit(
            label="Path:",
            labelwidth=width,
            browsebutton=QtWidgets.QPushButton("...", clicked=lambda: self._get_path(self, "assessments")),
        )
        self.assessments_sep = widgets.ParameterInputLine(label="Seperator:", labelwidth=width, default=",")
        self.assessments_skiprows = widgets.ParameterInputLine(
            label="Skip rows:", labelwidth=width, default=0
        )

        self.items_label = QtWidgets.QLabel(
            """Give the csv with items. The file should contain:
    - a column with item ids called "ItemID"
    - a column with realizations called "Realization". Fill in a value for seed questions, leave empty for target questions.
    - a column with scales called "Scale" Should be "uni" or "log".
    - optionally, a column with questions called "Question"."""
        )
        self.items_csv = widgets.ExtendedLineEdit(
            label="Path:",
            labelwidth=width,
            browsebutton=QtWidgets.QPushButton("...", clicked=lambda: self._get_path(self, "items")),
        )
        self.items_sep = widgets.ParameterInputLine(label="Seperator:", labelwidth=width, default=",")
        self.items_skiprows = widgets.ParameterInputLine(label="Skip rows:", labelwidth=width, default=0)

        for paraminp in [
            self.assessments_sep,
            self.assessments_skiprows,
            self.items_sep,
            self.items_skiprows,
        ]:
            paraminp.LineEdit.setMaximumWidth(40)
            paraminp.LineEdit.setMinimumWidth(20)

        # OK and Cancel buttons
        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.addButton("Import", QtWidgets.QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal, self)
        # button_box.addButton(self.close_button, QtWidgets.QDialogButtonBox.RejectRole)
        # button_box.accepted.connect(QtWidgets.QDialog.accept)

        self.setLayout(
            widgets.VLayout(
                [
                    widgets.SimpleGroupBox(
                        [
                            self.assessments_label,
                            self.assessments_csv,
                            self.assessments_sep,
                            self.assessments_skiprows,
                        ],
                        orientation="vertical",
                        title="Assessments CSV",
                    ),
                    widgets.SimpleGroupBox(
                        [
                            self.items_label,
                            self.items_csv,
                            self.items_sep,
                            self.items_skiprows,
                        ],
                        orientation="vertical",
                        title="Items CSV",
                    ),
                    widgets.HLine(),
                    widgets.HLayout(items=["stretch", self.buttonBox]),
                ]
            )
        )

    def accept(self):

        # Check if paths are filled
        if self.assessments_csv.get_value() == "":
            NotificationDialog("No path is given for assessments CSV.")
            return None

        if self.items_csv.get_value() == "":
            NotificationDialog("No path is given for items CSV.")
            return None

        super().accept()

    def _get_path(self, dialog, csv):

        # Set open file dialog settings
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtWidgets.QFileDialog.DontConfirmOverwrite
        # options |= QtWidgets.QFileDialog.DirectoryOnly

        # Set current dir
        currentdir = self.appsettings.value("currentdir", ".", type=str)

        # Open dialog to select file
        fname, ext = QtWidgets.QFileDialog.getSaveFileName(
            self, f"Anduryl - Select CSV with {csv}", currentdir, "CSV (*.csv)", options=options
        )
        if fname == "":
            return None
        else:
            fname = Path(fname.strip())
            ext = ext.split("*")[-1][:-1]
            if fname.suffix != ext:
                fname = fname.parent / (fname.name + ext)

        if csv == "assessments":
            dialog.assessments_csv.set_value(str(fname))
        elif csv == "items":
            dialog.items_csv.set_value(str(fname))
