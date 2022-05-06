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
    ex = MainWindow(app)
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

    # Verwijder de vragen over correlatie piping en macro
    items.remove_item("Correlatie piping")
    items.remove_item("Correlatie macro")
    # items.bounds[items.ids.index("Correlatie piping"), :] = [-0.1, 100.1]
    # items.bounds[items.ids.index("Correlatie macro"), :] = [-0.1, 100.1]

    # Overshoot voor vragen met 5 percentielen
    items.overshoots[12:-4, 0] = 0.02
    items.overshoots[-2:, 0] = 0.02

    # Verwijder de expert die de doelvragen niet heeft ingevuld
    # ex.project.experts.remove_expert("Exp F")

    # Zet een aantal vragen van expert D op NaN, omdat deze niet (te laat) zijn ingevuld
    ie = ex.project.experts.ids.index("Exp D")
    for item in ["Waterstandsverschil Maas", "Doorlatendheid 48-1 V"]:
        iq = ex.project.items.ids.index(item)
        ex.project.assessments.array[ie, :, iq] = np.nan

    # Voeg de units bij de vragen toe
    items.units[:] = [
        "Duration [h]",
        "Discharge [m$^3$/s]",
        "Wind speed [m/s]",
        "Water level difference [m]",
        "Number of failures [-]",
        "Number of piping failures [-]",
        "Discharge [m$^3$/s]",
        "Permeability [m/s]",
        "Coefficient of variation [-]",
        "Probability [-]",
        "Overtopping discharge [l/s/m/]",
        "Overtopping discharge [l/s/m/]",
        "Water level [m+NAP]",
        "Water level [m+NAP]",
        "Water level [m+NAP]",
        "Water level [m+NAP]",
        "Water level [m+NAP]",
        "Water level [m+NAP]",
        "Water level [m+NAP]",
        "Water level [m+NAP]",
        "Discharge [m$^3$/s]",
        "Discharge [m$^3$/s]",
    ]

    items.ids[:] = [
        "1. Residual strength overtopping experiment",
        "2. Maximum discharge Lobith december 2020",
        "3. Wind speed Deelen exceeded on average once per year",
        "4. Water level difference Meuse between 3000 and 4000 m$^3$/s",
        "5. Tyfoon Hagibis overtopping failure cases",
        "6. Tyfoon Hagibis piping failure cases",
        "7. Discharge through pipe during experiment",
        "8. Permeability subsoil 48-1 (mean)",
        "9. Permeability subsoil 48-1 (variation)",
        "10. Correlation high discharge Meuse and Rhine",
        "11. Critical overtopping discharge (Failure definition)",
        "12. Critical overtopping discharge (Breach)",
        "13. Failure-critical water level Piping (Failure definition)",
        "14. Failure-critical water level Piping (Breach)",
        "15. Failure-critical water level Macro stability (Failure definition)",
        "16. Failure-critical water level Macro stability (Breach)",
        "17. Uncertainty Piping (Failure definition)",
        "18. Uncertainty Piping (Breach)",
        "19. Uncertainty Macro stability (Failure definition)",
        "20. Uncertainty Macro stability (Breach)",
        "21. Failure-critical discharge for current dike safety",
        "22. Failure-critical discharge for dike safety matching safety standard",
    ]

    # Voeg DM's toe
    ex.expertswidget.add_decision_maker()
    ex.expertswidget.parameters_dialog

    ex.expertswidget.add_decision_maker()

    ex.expertswidget.add_decision_maker()

    sys.exit(app.exec_())
