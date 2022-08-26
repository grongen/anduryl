if __name__ == "__main__":

    # Import PyQt modules
    import sys
    import os
    import numpy as np

    # Import GUI
    from anduryl.core.main import Project
    from anduryl.ui.main import MainWindow
    from anduryl.io.settings import CalculationSettings

    # Open project
    # projectfile = sys.argv[1]
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\Arkansas.dtt"
    # projectfile = r"d:\Documents\GitHub\anduryl\cases\Daniela.dtt"
    projectfile = r"d:\Documents\GitHub\anduryl\cases\Erie Carps.dtt"

    project = Project()
    project.io.load_file(projectfile)

    itemopt_settings = CalculationSettings(
        id="DM1",
        name="Item opt.",
        weight="Item",
        overshoot=0.1,
        alpha=None,
        robustness=False,
        calpower=1.0,
        distribution="Metalog",
    )

    project.calculate_decision_maker(itemopt_settings)
