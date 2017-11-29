#!/usr/bin/env python

from setuptools import setup, find_packages

# txrm2nexus setup.py for usage of setuptools

# The version is updated automatically with bumpversion
# Do not update manually
__version = '10.4.2-alpha'

long_description = """ xrm2h5 is a file format converter application which
allows to convert single image xrm files into its corresponding single image
hdf5 files.

xrm2nexus is a file format converter application
which allows to convert .xrm single image files (output of the
TXM Microscope at BL09-Mistral), into HDF5 files.

txrm2nexus is a file format converter application
which allows to convert .xrm and .txrm image stack files (output of the
TXM Microscope at BL09-Mistral), into HDF5 files.

'mosaic2nexus' allows to convert xrm mosaics generated by the TXM Microscope
into HDF5.

'normalize' is a script to normalize images using the FF, exposure times
and currents.

'magnify' is a script used to magnify the images of the spectroscopy stack
 to different ratios, according to a given file containing an array of
 magnification ratios.

Scripts for automating the conversion and normalization for many tomographies
placed in different folders are also provided (autotxrm2nexus, 
automosaic2nexus, autonormalize).
"""

classifiers = [
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering',
    'Topic :: Software Development :: Libraries',

    # Pick your license as you wish (should match "license" above)
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 2.7',
]


setup(
    name='txrm2nexus',
    version=__version,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'xrm2h5 = txm2nexuslib.scripts.xrm2h5:main',
            'xrm2nexus = txm2nexuslib.scripts.xrm2nexus:main',
            'manytomos2nexus = txm2nexuslib.scripts.manytomos2nexus:main',
            'txrm2nexus = txm2nexuslib.scripts.txrm2nexus:main',
            'mosaic2nexus = txm2nexuslib.scripts.mosaic2nexus:main',
            'normalize = txm2nexuslib.scripts.normalize:main',
            'magnify = txm2nexuslib.scripts.magnify:main',
            'autotxrm2nexus = txm2nexuslib.scripts.autotxrm2nexus:main',
            'automosaic2nexus = txm2nexuslib.scripts.automosaic2nexus:main',
            'autonormalize = txm2nexuslib.scripts.autonormalize:main']
    },
    author='Marc Rosanes, Carlos Falcon, Zbigniew Reszela, Carlos Pascual',
    author_email='mrosanes@cells.es, cfalcon@cells.es, zreszela@cells.es, '
                 'cpascual@cells.es',
    maintainer='ctgensoft',
    maintainer_email='ctgensoft@cells.es',
    url='https://git.cells.es/controls/txrm2nexus',
    keywords='APP',
    license='GPLv3',
    description='Conversion from xrm and txrm to hdf5',
    long_description=long_description,
    requires=['setuptools (>=1.1)'],
    install_requires=['numpy', 'h5py', 'tinydb'],
    classifiers=classifiers
)

