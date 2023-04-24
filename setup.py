from setuptools import setup, find_packages

setup(
    name='anduryl',
    version='1.2.2',    
    description='A Python module and GUI for expert elicitation based on Cooke\'s classical method.',
    url='https://github.com/grongen/anduryl',
    author='Guus Rongen, Marcel \'t Hart, Georgios Leontaris, Oswaldo Morales Nápoles',
    author_email='g.w.f.rongen@tudelft.nl',
    license='GNU license',
    packages=['anduryl', 'anduryl/core', 'anduryl/io', 'anduryl/ui'],
    install_requires=['numpy', 'PyQt5', 'matplotlib'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: Microsoft :: Windows',        
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
    ],
    include_package_data=True,
    package_data={'anduryl/data': ['data/icon.ico', 'data/icon.gif', 'data/splash_loading.png']},
)
