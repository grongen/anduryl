call conda config --add channels conda-forge
call conda config --set channel_priority strict 
call conda create -y -n anduryl python=3.10 pip setuptools Pyinstaller pydantic
call conda activate anduryl
REM call pip install [DOWNLOAD VANILLA WHEEL FROM https://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy]
call pip install pyqt5 matplotlib
REM conda remove --name openblas --all