indextxt = """.. Anduryl documentation master file

Welcome to Anduryl's documentation!
===================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

{}

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""

rsttext = """{file}
------------------------------

.. automodule:: {module}
    :members:
    :undoc-members:
    :show-inheritance:
"""

toctext = """{name}
===================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

{lines}
"""

path = '..\..'
index = []

import os

for root, dirs, files in os.walk(path):
    # path = root.split(os.sep)
    # print((len(path) - 1) * '---', os.path.basename(root))
    # for file in files:
        # print(len(path) * '---', file)

    if 'doc' in root:
        continue

    for d in dirs:
        if d == 'doc' or d.startswith('_'):
            continue

        lines = '\n'.join(['   '+d+'/'+file[:-3] for file in os.listdir(os.path.join(root, d)) if file.endswith('.py')])
        with open(d+'.rst', 'w') as f:
            f.write(toctext.format(name=d, lines=lines))

        index.append(f'   {d}')

    for file in files:
        if file.endswith('.py') and not file.startswith('_'):
            # Add to index
            line = os.path.join(root.replace(path, ''), file)
            line = line.replace('.py', '')
            if line.startswith('\\'):
                line = line[1:]

            index.append('   ' + line.replace('\\', '/'))

            # Add file
            rstfile = line+'.rst'

            if os.path.dirname(rstfile) and not os.path.exists(os.path.dirname(rstfile)):
                os.mkdir(os.path.dirname(rstfile))

            with open(rstfile, 'w') as f:
                f.write(rsttext.format(file=file, module='anduryl.'+line.replace('\\', '.')))

with open('index.rst', 'w') as f:
    f.write(indextxt.format('\n'.join(index)))