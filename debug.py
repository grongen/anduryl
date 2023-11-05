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
    from anduryl.io.settings import CalculationSettings, CalibrationMethod, Distribution

    # Create main window
    ex = MainWindow(app)
    splash.close()

    # Open project
    # projectfile = sys.argv[1]
    # projectfile = r"d:\TUD\P03 - Length effects\faalkansen_rijntakken_update.json"
    # projectfile = r"d:\TUD\P03 - Length effects\faalkansen_rijntakken_update_excalibur.dtt"
    # projectfile = r"d:\TUD\P03 - Length effects\tst.json"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\CWD.dtt"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\Arsenic D-R.dtt"
    projectfile = r"d:\TUD\P11 - Metalog\allcases2\Arkansas.json"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\Arkansas.dtt"
    # projectfile = r"d:\TUD\P08 - Afvoerstatistiek EJ\Data\Elicitation\meuse_discharges_expertsessie.json"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\ebbp.dtt"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\Biol agents.dtt"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\ATCEP error.dtt"

    ex.open_project(fname=projectfile)

    # equal_settings = CalculationSettings(
    #     id="EQ",
    #     name='Equal',
    #     weight='Equal',
    #     overshoot=0.1,
    #     alpha=0.0,
    #     optimisation=False,
    #     robustness=False,
    #     calpower=1.0,
    #     distribution=Distribution.PWL,
    #     calibration_method=CalibrationMethod.LR
    # )

    # equal_settings2 = CalculationSettings(
    #     id="EQ2",
    #     name='Equal2',
    #     weight='Equal',
    #     overshoot=0.1,
    #     alpha=0.0,
    #     optimisation=False,
    #     robustness=False,
    #     calpower=1.0,
    #     distribution=Distribution.METALOG,
    #     calibration_method=CalibrationMethod.LR
    # )

    # itemopt_settings = CalculationSettings(
    #     id="DM1",
    #     name="Item opt.",
    #     weight="Item",
    #     overshoot=0.1,
    #     optimisation=True,
    #     robustness=False,
    #     calpower=1.0,
    #     distribution="Metalog",
    # )

    settings1 = CalculationSettings(
        id="DM2",
        name="Global no opt.",
        weight="Global",
        overshoot=0.1,
        alpha=None, # TODO: For optimisation, alpha should be None. This is not checked
        optimisation=False,
        robustness=True,
        calpower=1.0,
        distribution=Distribution.METALOG,
        calibration_method=CalibrationMethod.AD
    )


    # globalnonopt_settings = CalculationSettings(
    #     id="DM1",
    #     name="Global no opt.",
    #     weight="Global",
    #     overshoot=0.1,
    #     alpha=None, # TODO: For optimisation, alpha should be None. This is not checked
    #     optimisation=True,
    #     robustness=True,
    #     calpower=1.0,
    #     distribution=Distribution.METALOG,
    #     calibration_method=CalibrationMethod.AD
    # )

    # ex.project.experts.remove_expert("AR03")

    ex.project.calculate_decision_maker(settings1)
    # ex.project.calculate_decision_maker(globalnonopt_settings)
    # print()
    # ex.project.calculate_decision_maker(equal_settings2)

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


