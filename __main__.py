"""Top-level package for delft3dfmpy."""

__author__ = """Guus Rongen, Marcel 't Hart, Georgios Leontaris, Oswaldo Morales Nápoles"""
__email__ = 'g.w.f.rongen@tudelft.nl'
__version__ = '1.2.0'

if __name__ == '__main__':

    # Import GUI modules
    from anduryl.ui.main import MainWindow
    from PyQt5 import QtWidgets
    import sys

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationVersion(__version__)

    # Create main window
    ex = MainWindow()
    # ex.start_profiling()

    # Open project
    if len(sys.argv) > 1:
        ex.open_project(fname=sys.argv[1])

    sys.exit(app.exec_())
