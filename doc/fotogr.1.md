fotogr (1)
==================

NAME
----

fotogr - Search for tagged images

SYNOPSIS
--------

fotogr [-s] [-d dirs] condition [condition ...]


DESCRIPTION
-----------

Search inside the current directory (recursively) for all files tagged
with the given patterns/keywords.

OPTIONAL FLAGS
--------------

| -i              | ignore case (this is the default) |
| +i              | don't ignore case (case is ignored by default) |
| -t              | taglines: print out the tag lines that match, not just the filenames, in case you need to narrow the search |
| -D              | show verbose output for debugging |
| -d dir,dir,dir  | comma-separated list of directories to use (else .) Each dir may be a shell-style pattern, e.g. 19??,20?? |


DETAILED USAGE
-----------------------------

fotogr can understand simple logical combinations.
Each keyword can specify one of three types of patterns:

  1. Starts with +: must be present (AND).
  2. Starts with -: must NOT be present (NOT).
  3. Starts with neither: one of these must be present (OR).


AUTHOR
------

Akkana Peck.

COPYRIGHT
---------

Copyright (C) 2013,2016,2019,2020,2022 Akkana Peck.
Part of Metapho, which is free software,
licensed under the GNU Public License version 2 (or later).

SEE ALSO
--------

The most recent version of `metapho`, and more information about it, is at:
https://github.com/akkana/metapho
