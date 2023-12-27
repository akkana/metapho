#!/usr/bin/env python2

# metapho: an image tagger and viewer.

# Copyright 2013-2021 by Akkana Peck: share and enjoy under the GPL v2 or later.

'''metapho: an image tagger and viewer.'''

__version__ = "1.1b3"
__author__ = "Akkana Peck <akkana@shallowsky.com>"
__license__ = "GPL v2+"
__all__ = [ 'Image', 'Tagger' ]

from .metapho import *

# Don't import gtkpho classes automatically;
# users may not want or need the GUI parts.


