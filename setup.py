#
# setup.py file for netops
#
from numpy.distutils.core import setup

### Regular setup stuff ######################################################

s_args = {'name'         : 'netops',
          'version'      : '0.5.0',
          'description'  : 'Network Operations utilities',
          'author'       : 'Nevada Seismological Lab',
          'url'          : 'https//github.com/NVSeismoLab',
          'packages'     : ['netops', 'netops.converters', 'netops.packets','netops.util'],
          'package_data' : {'netops': [] },
          'ext_modules'  : [],
}

# Go
setup(**s_args)
