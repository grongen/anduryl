if __name__ == '__main__':

    # Import PyQt modules
    from PyQt5 import QtWidgets, QtGui, QtCore
    import sys
    import os

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)

    # Create and display the splash screen
    splashpath = os.path.join(os.path.dirname(__file__), '..', 'data', 'splash_loading.png')
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(splashpath), QtCore.Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    # Import GUI
    sys.path.append('..')
    from anduryl.core.main import Project
    from anduryl.ui.main import MainWindow

    # Create main window
    ex = MainWindow()
    splash.close()
    
    # Open project
    projectfile = r'd:\Downloads\opzet_vragenlijst.json'
    
    ex.open_project(fname=projectfile)
    ex.setCursorNormal()

    ex.itemswidget.set_bounds(False)

    sys.exit(app.exec_())
