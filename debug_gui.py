if __name__ == '__main__':

    # Import PyQt modules
    from PyQt5 import QtWidgets, QtGui, QtCore, Qt
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
    projectfile = r"d:/Documents/GitHub/anduryl/data/7quants.dtt"
    projectfile = r"d:\TUD\P03 - Length effects\faalkansen_rijntakken.json" 
    
    ex.open_project(fname=projectfile)

    ex.project.items.use_quantiles[:12, 0] = False
    ex.project.items.use_quantiles[:12, 2] = False
    ex.project.items.use_quantiles[-4:-2, 0] = False
    ex.project.items.use_quantiles[-4:-2, 2] = False

       
    ex.setCursorNormal()
    # ex.itemswidget.set_bounds(False)

    # Check answers
    import numpy as np

    for iq in range(len(ex.project.items.ids)):
        use = ex.project.items.use_quantiles[iq]
        answers = ex.project.assessments.array[:, use, iq]
        diff = np.diff(answers, axis=1)
        idx = ~((diff > 0).all(axis=1) | np.isnan(diff).any(axis=1))
        if idx.any():
            print(ex.project.items.ids[iq], [ex.project.experts.ids[i] for i in np.where(idx)[0]])


    items = ex.project.items
    # Aantal falende dijken kan niet lager dan 0. Omdat 0 niet kan (sommige experts
    # hebben dit als 5de percentiel geantwoord) nemen we -0.001
    items.item_bounds[items.ids.index('Tyfoon Hagibis overloop'), 0] = -0.001
    items.item_bounds[items.ids.index('Tyfoon Hagibis piping'), 0] = -0.001

    # Correlaties
    items.item_bounds[items.ids.index('Correlatie Maas en Rijn'), :] = [-0.001, 1.001]
    items.item_bounds[items.ids.index('Correlatie piping'), :] = [-0.1, 100.1]
    items.item_bounds[items.ids.index('Correlatie macro'), :] = [-0.1, 100.1]

    # Overshoot voor vragen met 5 percentielen
    items.item_overshoot[12:-4, 0] = 0.02
    items.item_overshoot[-2:, 0] = 0.02

    ex.project.experts.remove_expert('Exp F')

    # ex.itemswidget.set_bounds(None)
    print('Something')

    sys.exit(app.exec_())