#
# setup.py file for netops
#
#try:
#    import setuptools
#except ImportError:
#    pass

from setuptools import setup

### Regular setup stuff ######################################################

s_args = {'name': 'nsl.common',
          'version': '0.6.0',
          'description': 'NSL Common libraries and utilities for Python',
          'author': 'Nevada Seismological Lab',
          'url': 'https//github.com/NVSeismoLab',
          'packages': ['nsl',
                       'nsl.common',
                       'nsl.common.config',
                       'nsl.antelope',
                       'nsl.antelope.base',
                       'nsl.antelope.packets',
                       'nsl.antelope.pf',
                       'nsl.antelope.util',
                       'nsl.converters', 
                       'nsl.obspy',
                       'nsl.obspy.patches'
                       'nsl.util'
                       ],
          'package_data': {'nsl': [] },
}

# Go
setup(**s_args)
