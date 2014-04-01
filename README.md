nsl.commons
===========
Common libraries and utilities for NSL

This is a next-gen work in progress, there is no way this code passes
all tests yet, so, here be dragons.

The following sub-packages are available:

nsl.common
----------
Common functions and libs for all programs

* `config` - configuration files
* `util` - utilities

nsl.antelope
------------
Utilities for using Antelope

* `base` - base classes
* `packets` - various ORB packets
* `pf` - standardized pf functions
* `util` - general utils

nsl.converters
--------------
Conversion classes, work in progress (Mostly for QuakeML conversion)

* `CSSToEventConverter`
* `AntelopeToEventConverter`
* `DBToQuakeMLConverter`
* `ichinose` - functions to convert MT output
* `db2qml` - custom Converter for scripts/command line

nsl.obspy
---------
Utilites for using ObsPy

* `patches` - patches for new features and older versions
* `util` - add-on utilities for using ObsPy with itself

nsl.scripts
-----------
* `db2quakeml` - CLI script for converting CSS flat text file to QuakeML

nsl.util
--------
Package-wide utilities
(Stub/backwards compat for now)


License
=======
Copyright 2014 Mark C. Williams 
at [Nevada Seismological Laboratory](http://www.seismo.unr.edu/Faculty/29)

Under the GPL for now, some or all of this code may be released under
an additional license, if the situation warrants it.

GPL
---
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

