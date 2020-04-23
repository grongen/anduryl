# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import shutil

block_cipher = None

# Import list of binaries to exclude
with open('binaries_to_remove.txt', 'r') as f:
    binaries_to_remove = [file.lower() for file in f.read().split('\n') if not file.startswith('#')] 

# Collect documentation
docpaths = []
docbase = '../doc/build/html'
for root, dirs, files in os.walk(docbase):
    docpaths += [os.path.join(root, file) for file in files]
docdata = [(path, os.path.split(path.replace(docbase, 'doc'))[0]) for path in docpaths]

# Add icon
docdata.append(('../data/icon.ico', 'data'))

# Find qwindows.dll
for path in sys.path:
    if path.endswith('openblas'):
        qwindowsdll = os.path.join(path, 'Lib/site-packages/PyQt5/Qt/plugins/platforms/qwindows.dll')
        assert os.path.exists(qwindowsdll)
        break
else:
    raise OSError('Could not find qwindows.dll')

# Analysis class
a = Analysis(
    ['../__main__.py'],
    pathex=[],
    binaries=[(qwindowsdll, 'platforms')],
    datas=docdata,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# Remove binaries
to_remove = []
for i, (file, _, cat) in enumerate(a.binaries):
    if (file.strip().lower() in binaries_to_remove) or (file.strip().lower().split('\\')[-1] in binaries_to_remove):
        to_remove.append(i)
for i in reversed(to_remove):
    del a.binaries[i]

# Remove data to exclude
to_remove = []
for i, (path, _, _) in enumerate(a.datas):
    if 'pyqt5\\qt\\qml' in path.lower():
        to_remove.append(i)
    if 'pyqt5\\translations' in path.lower():
        to_remove.append(i)
    elif 'pyqt5\\qt\\bin' in path.lower():
        to_remove.append(i)
    elif 'mpl-data\\sample_data' in path.lower():
        to_remove.append(i)
    elif 'mpl-data\\fonts' in path.lower():
        to_remove.append(i)

for i in reversed(to_remove):
    del a.datas[i]

# Create archive
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Anduryl',
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon='../data/icon.ico'
)
