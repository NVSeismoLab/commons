#
# setup.py file for netops
#
from setuptools import setup
# Directory of the current file in the (hopefully) most reliable way
# possible, according to krischer
import sys
import os
import inspect
SETUP_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(
    inspect.currentframe())))

# Import the version string.
UTIL_PATH = os.path.join(SETUP_DIRECTORY, "nsl", "util")
sys.path.insert(0, UTIL_PATH)
from version import get_git_version  # @UnresolvedImport
sys.path.pop(0)

s_args = {'name': 'nsl.common',
          'version': get_git_version(),
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
                       'nsl.antelope.util',
                       'nsl.converters', 
                       'nsl.obspy',
                       'nsl.obspy.patches',
                       'nsl.util',
                       ],
          'package_data': {'nsl': ['RELEASE-VERSION'] },
}

# Go
setup(**s_args)
