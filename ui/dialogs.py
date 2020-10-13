import os
import sys
from PyQt5 import QtGui, QtWidgets, QtCore


def get_icon():
    # In case of PyInstaller exe
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
        iconpath = os.path.join(application_path, 'data', 'icon.ico')
    # In case of regular python
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        iconpath = os.path.join(application_path, '..', 'data', 'icon.ico')

    return QtGui.QIcon(iconpath)

class NotificationDialog(QtWidgets.QMessageBox):
    """
    Custom notification dialog
    """

    def __init__(self, text, severity='information', details=''):
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
        
        if severity == 'warning':
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
            self.setWindowTitle("Warning")
        elif severity == 'critical':
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
            self.setWindowTitle("Critical")
        elif severity == 'information':
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