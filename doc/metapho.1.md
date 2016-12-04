METAPHO l "Feb 17 2013" "User Manuals"
======================================

NAME
----

metapho - view images and tag them with words or phrases

SYNOPSIS
--------

metapho *file* ...

DESCRIPTION
-----------

`metapho` lets you tag large numbers of images as efficiently as possible.
Although it uses a graphical user interface, it's intended
to be controllable entirely through the keyboard.

It offers two modes, somewhat similar to the vi editor.
Normally you're in "navigational" mode, where you can rapidly
move between photos and view and toggle tags.
Clicking in a text entry, or typing Return or <Ctrl>Space,
will let you add new tags. Hit ESC, Return, or <Ctrl>Space to
leave entry mode and return to navigational mode.

Tags will be written to a file named Tags.
Metapho tries to be smart about where to write the Tags file,
using the highest common directory of the images passed to it
on the command line. It will also read tags in from any Tags
files that already exist in any of the image directories,
and will save those tags (unless changed by the user) along
with any new tags added.

KEY BINDINGS
------------

Metapho obeys the following keys:

`[space]`
Go to next image.

`[backspace]`
Go to previous image

`r`, `t`, `[right-arrow]`
Rotate right (clockwise)

`R`, `T`, `l`, `L`, `[left-arrow]`
Rotate left (counter-clockwise)

`[up-arrow]`, `[down-arrow]`
Rotate 180 degrees.

`Home`
Go back to the first image.

`End`
Go to the last image.

`<Ctrl>q`
Quit the application, writing any changes to the Tags file.

`<Ctrl>d`
Delete this image file from disk.
This will bring up a confirmation dialog; clicking OK or
typing another d or <Ctrl>d deletes the file.

`a` through `z` or `A` through `Z`
Toggle the appropriate tag for this image.

`Return`
If in navigation mode: activate the first blank tag and let you type in it.
If in entry mode: leave entry mode and return to navigation mode.

`<Ctrl>Space`
Stop typing in a tag field and move to the next image;
or, if not currently in a tag field, activate the next tag and
shift focus there.

`Escape`
Ensure focus is not in a text field, so any characters typed
will be navigational.

`<Ctrl>U`
Forget all tags for the current image.
By default, when moving from one image to a new image that has no tags yet,
metapho will copy the tags from the previous image.
Use <Ctrl>U to turn these off.

`/`
Search for tags matching whatever you type.
Use Return or ESC to get out of search mode.

AUTHOR
------

Akkana Peck, with a lot of design help from John Sturdy.

COPYRIGHT
---------

Copyright &copy; 2013,2016 Akkana Peck
Metapho is free software, licensed under the GNU Public License version 2.

SEE ALSO
--------

The most recent version of `metapho`, and more information about it, is at:
https://github.com/akkana/metapho
