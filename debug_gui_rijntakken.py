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
    sys.path.append("..")
    from anduryl.core.main import Project
    from anduryl.ui.main import MainWindow

    # Create main window
    ex = MainWindow()
    splash.close()

    # Open project
    # projectfile = r"d:/Documents/GitHub/anduryl/data/7quants.dtt"
    projectfile = r"d:\TUD\P03 - Length effects\faalkansen_rijntakken_update.json"
    # projectfile = r"d:\TUD\P03 - Length effects\faalkansen_rijntakken.json"

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
    items.bounds[items.ids.index("Tyfoon Hagibis overloop"), 0] = -0.001
    items.bounds[items.ids.index("Tyfoon Hagibis piping"), 0] = -0.001

    # Correlaties
    items.bounds[items.ids.index("Correlatie Maas en Rijn"), :] = [-0.001, 1.001]
    items.bounds[items.ids.index("Correlatie piping"), :] = [-0.1, 100.1]
    items.bounds[items.ids.index("Correlatie macro"), :] = [-0.1, 100.1]

    # Overshoot voor vragen met 5 percentielen
    items.overshoots[12:-4, 0] = 0.02
    items.overshoots[-2:, 0] = 0.02

    # ex.project.experts.remove_expert('Exp F')

    ie = ex.project.experts.ids.index("Exp D")
    for item in ["Waterstandsverschil Maas", "Doorlatendheid 48-1 V"]:
        iq = ex.project.items.ids.index(item)
        ex.project.assessments.array[ie, :, iq] = np.nan

    # # Note that not specifying alpha results in optimization in case of global or item weights.
    # ex.project.calculate_decision_maker(
    #     weight_type=WeightType.GLOBAL,
    #     overshoot=0.1,
    #     exp_id="Global",
    #     calpower=1.0,
    #     exp_name="Global, no opt.",
    #     alpha=0.0,
    #     overwrite=True,
    # )

    # ex.project.calculate_decision_maker(
    #     weight_type="item",
    #     overshoot=0.1,
    #     exp_id="Item",
    #     calpower=1.0,
    #     exp_name="Item, no opt.",
    #     alpha=0.0,
    #     overwrite=True,
    # )

    # # Calculate decision maker with user defined weights
    # ex.project.calculate_decision_maker(
    #     weight_type="equal",
    #     overshoot=0.1,
    #     exp_id="Equal",
    #     calpower=1.0,
    #     exp_name="Equal weights",
    #     alpha=None,
    #     overwrite=True,
    # )

    # ex.project.calculate_expert_robustness(WeightType.GLOBAL, overshoot=0.1, max_exclude=2, min_exclude=0)

    print("Something")

    sys.exit(app.exec_())
