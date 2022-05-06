if __name__ == "__main__":

    # Import PyQt modules
    from PyQt5 import QtWidgets, QtGui, QtCore, Qt
    import sys
    import os
    import numpy as np

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)

    # Create and display the splash screen
    splashpath = os.path.join(os.path.dirname(__file__), "..", "data", "splash_loading.png")
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(splashpath), QtCore.Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    # Import GUI
    from anduryl.core.main import Project
    from anduryl.ui.main import MainWindow

    # Create main window
    ex = MainWindow(app)
    splash.close()

    # Open project
    projectfile = sys.argv[1]
    projectfile = r"d:\TUD\P03 - Length effects\faalkansen_rijntakken_update.json"
    # projectfile = r"d:\TUD\P03 - Length effects\faalkansen_rijntakken_update_excalibur.dtt"
    # projectfile = r"d:\TUD\P03 - Length effects\tst.json"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\puig-oil.dtt"

    ex.open_project(fname=projectfile)

    # ex.expertswidget.add_decision_maker()

    # ex.expertswidget.add_decision_maker()

    # ex.expertswidget.add_decision_maker()

    # # Get results widget
    # w = ex.resultswidget.tabs.widget(0)
    # Plot items
    # w.plot_items()

    # dialog = w.plot_dialog
    # dialog.save_all_figures()

    sys.exit(app.exec_())
