#
# setup.py file for netops
#
#try:
#    import setuptools
#except ImportError:
#    pass

from numpy.distutils.core import setup

### Regular setup stuff ######################################################

s_args = {'name'         : 'netops',
          'version'      : '0.5.4',
          'description'  : 'Network Operations utilities',
          'author'       : 'Nevada Seismological Lab',
          'url'          : 'https//github.com/NVSeismoLab',
          'packages'     : ['netops', 'netops.converters', 'netops.packets','netops.util'],
          'package_data' : {'netops': [] },
          'ext_modules'  : [],
          'install_requires': ['curds2', 'obspy'],
}

# Go
setup(**s_args)
