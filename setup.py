#
# setup.py file for netops
#
try:
    import setuptools
except ImportError:
    print('Setuptools is needed to automatically resolve dependencies')

from numpy.distutils.core import setup

### Regular setup stuff ######################################################

s_args = {'name'         : 'netops',
          'version'      : '0.5.3',
          'description'  : 'Network Operations utilities',
          'author'       : 'Nevada Seismological Lab',
          'url'          : 'https//github.com/NVSeismoLab',
          'packages'     : ['netops', 'netops.converters', 'netops.packets','netops.util'],
          'package_data' : {'netops': [] },
          'ext_modules'  : [],
          'install_requires': ['obspy','curds2'],
          'dependency_links': ['https://github.com/NVSeismoLab/curds2/archive/master.zip#egg=curds2']
}

# Go
setup(**s_args)
