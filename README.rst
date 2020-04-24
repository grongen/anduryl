============================
Anduryl
============================

A Python module and GUI for expert elicitation based on Cooke's classical method.

The software is based on an older application called Excalibur, and previous MATLAB and Python versions described in ![ANDURIL — A MATLAB toolbox for ANalysis and Decisions with UnceRtaInty: Learning from expert judgments](https://www.sciencedirect.com/science/article/pii/S2352711018300608?via%3Dihub) and ![Update (1.1) to ANDURIL — A MATLAB toolbox for ANalysis and Decisions with UnceRtaInty: Learning from expert judgments: ANDURYL](https://www.sciencedirect.com/science/article/pii/S2352711019302419?via%3Dihub).

* Free software: GNU license

Features
--------

* Set up your structured expert judgment project
* Calculate decision makers
* Robustness analysis
* Visualizations
* Work from a GUI or script/notebook

Installation
------------
This module cannot be installed with pip or conda. To use it:

1.  Clone or download the repository;

2.	For running the stand alone GUI application, download the exe from here: https://github.com/grongen/anduryl/blob/master/pyinstaller/dist/Anduryl.exe

3.  For running the GUI from the python scripts, open an Anaconda command prompt in the github directory and run `python -m anduryl`.

4.  To import the anduryl module in your script or notebook, Python needs to find the anduryl module on one of the following directories:

    * the Python working directory. This can be checked in Python with::

        import os
        print(os.getcwd())

    * the site-packages directory of the Python installation in the correct environment (see below). Using anaconda, this is usually C:/users/[name]/AppData/Local/Continuum/Anaconda3/Lib/site-packages

    * a user defined directory, added within the script with::

        import sys
        sys.path.append('path/to/directory')

    If the downloaded directory is named "anduryl-master", rename it to "anduryl"

To get all the required dependencies working, it is advised to:

1.  Install a Anaconda Python distribution: https://www.anaconda.com/distribution/

2.  Create an environment with the required modules, by executing the following commands in an anaconda command prompt::

        conda config --add channels conda-forge
		conda config --set channel_priority strict 
        conda create --name [your environment name] numpy pyqt5 matplotlib

3.  Activate the created environment in an anaconda command prompt (activate [your environment name]) before running your notebook or script. A jupyter notebook or command prompt for the environment can also be launched from the Anaconda Navigator.

4.  For more information on how to use environments, see: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

Usage
-----
The documentation provides a quickstart guide. The documentation can be accessed from the GUI menu under 'help'.
For using the module directly from code or notebook, see the example notebook under https://htmlpreview.github.io/?https://github.com/grongen/anduryl/blob/master/notebooks/Example_Anduryl_with_scripting.html

Build
-----
If you want to use PyInstaller to build the GUI yourself, view the readme in the pyinstaller directory.
