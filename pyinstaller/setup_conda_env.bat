call conda config --add channels conda-forge
call conda config --set channel_priority strict 
call conda create -y -n openblas pip numpy "blas=*=openblas" setuptools
call conda activate openblas
call pip install pyqt5 matplotlib
call pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip
REM conda remove --name openblas --all