notags (1)
==================

NAME
----

notags - search for files and directories that need metapho-style tagging

SYNOPSIS
--------

notags

DESCRIPTION
-----------

Change directory to the root of an image directory, then run notags
with no arguments.

It will search recursively for files named Tags (or the older,
deprecated Keywords), and will report whether there are any
untagged files, any directories containing taggable files but no
Tags file, or files referenced in a Tags file that no longer exist
on disk.

You can then use metapho to tag anything that needs it.


AUTHOR
------

Akkana Peck.

COPYRIGHT
---------

Copyright &copy; 2013,2016,2019 Akkana Peck.
Metapho is free software, licensed under the GNU Public License version 2.

SEE ALSO
--------

The most recent version of `metapho`, and more information about it, is at:
https://github.com/akkana/metapho
