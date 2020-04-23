To build Anduryl as a stand alone executable:

1.	Create a conda environment with the required modules, this can be done by running "setup_conda_env.bat". This batch file should be run from Anaconda command prompt if Python has not been added to the system environmental variable PATH (default). Note that the latest distributions are downloaded, which may not always result in a working combinations with PyInstaller.

2.	Run the "build.bat" file, this builds a one file executable.