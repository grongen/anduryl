"""Top-level package for delft3dfmpy."""

__author__ = """Guus Rongen, Marcel 't Hart, Georgios Leontaris, Oswaldo Morales Nápoles"""
__email__ = "g.w.f.rongen@tudelft.nl"
__version__ = "1.2.1"

if __name__ == "__main__":

    # Import PyQt modules
    from PyQt5 import QtWidgets, QtGui, QtCore
    import sys
    import os
    from pathlib import Path

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)

    # Create and display the splash screen
    # In case of PyInstaller exe
    if getattr(sys, "frozen", False):
        splashpath = os.path.join(sys._MEIPASS, "data", "splash_loading.png")
    # In case of regular python
    else:
        currentdir = Path(__file__).parent
        splashpath = currentdir / ".." / "data" / "splash_loading.png"
        if not splashpath.exists():
            splashpath = currentdir / "data" / "splash_loading.png"
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(str(splashpath)), QtCore.Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    app.setApplicationVersion(__version__)

    # Import GUI
    from anduryl.core.main import Project
    from anduryl.ui.main import MainWindow

    # Create main window
    ex = MainWindow(app)
    splash.close()
    # ex.start_profiling()

    # Open project
    if len(sys.argv) > 1:
        ex.open_project(fname=sys.argv[1])
        ex.setCursorNormal()

    sys.exit(app.exec_())
