#
# setup.py file for netops
#
from setuptools import setup

s_args = {'name': 'nsl.common',
          'version': '0.10.1',
          'description': 'NSL Common libraries and utilities for Python',
          'author': 'Nevada Seismological Lab',
          'url': 'https//github.com/NVSeismoLab',
          'packages': ['nsl',
                       'nsl.common',
                       'nsl.common.logging',
                       'nsl.antelope',
                       'nsl.antelope.base',
                       'nsl.antelope.packets',
                       'nsl.antelope.rows',
                       'nsl.converters', 
                       'nsl.obspy',
                       'nsl.obspy.patches',
                       'nsl.util',
                       ],
          'package_data': {'nsl': [] },
}

# Go
setup(**s_args)
