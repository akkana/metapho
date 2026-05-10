pho(1)
======

NAME
----

pho - an image viewer

DESCRIPTION
-----------
Pho displays images.
It is intended as a lightweight and fast viewer,
optimized for rapidly going through large numbers of uploaded images.

Pho is entirely keyboard driven,
and allows for interactive rotation and taking of notes on each image.
It resizes after rotations and will always attempt to show
the image as large as possible.  The final rotation reached for
each image will be remembered and printed when the program exits
(for use with a batch image rotation script).

Pho can also remember up to ten lists of images (numbered 0-9) which can
correspond to anything the user wishes. The image lists will be printed
to standard output when pho exits. Use this to keep notes on which
images you want to save to the web, which images contain images
of your dog, etc.

COMMAND-LINE OPTIONS
--------------------

-p
    "Presentation mode": display in full screen mode with a black background
    (if the window manager allows it). In presentation mode, if you zoom in
    and need to move (pan) in the image, drag with the middle mouse button.

-P
    Force non-presentation mode (e.g. if you set PHO_ARGS=-p).

-mN
    Use monitor number N.

-sN
    Automatic Slideshow mode, where N is the delay in seconds.
    For example, -s5 will show pause 5 seconds between images.
    -s0 means no delay.

-d
    Debug mode: print debugging messages to standard output.

-h
    Help: print a usage statement.

-v
    Verbose help: print a summary of key bindings.

ENVIRONMENT VARIABLES
---------------------

PHO_ARGS: default flag settings
(e.g. set it to -p to use presentation mode by default).
Any flags given on the command line will override these settings.

PHO_CMD: the command to call when you press the 'g' key.
Include a %s to represent the filename of the current image.
(Defaults to gimp %s).

KEY BINDINGS
------------

When pho is running, it obeys the following keys:

[space], [Page Down]
    Go to next image. Or cancel slideshow mode, if active.

[backspace], [Page Up]
    Go to previous image

[right-arrow]
    Rotate right (clockwise)

[left-arrow]
    Rotate left (counter-clockwise)

[up-arrow], [down-arrow]
    Rotate 180 degrees.

Home
    Go to the first image.

End
    Go to the last image

d
    Delete (will bring up a confirmation dialog; clicking OK or
    typing another d deletes the file).

i
   Show a dialog with information about the image, including EXIF tags.

0 through 9
    Add the image to the appropriate notes list

f
    Toggle in/out of "full size mode".  Images will be shown at their
    native size, even if it's bigger than the screen size.
    (Hint: Many window managers let you move oversized windows with alt-drag.)

p
    Toggle in/out of "presentation (full screen) mode".
    If the window manager permits, pho will take up the full screen
    with the image (if smaller) centered.

+, =
    Magnify: show the image at twice the current size.

-
.TP
    Unmagnify: show the image at half the current size..TP

q
    Quit

ENVIRONMENT
-----------

Pho checks for the environment variable PHO_ARGS, which can contain flags
to use as default arguments.
For example, PHO_ARGS=p will always run pho in presentation mode (unless
you pass -P to turn off that mode).

AUTHOR
------
Akkana Peck

COPYRIGHT
Copyright \(co 2002-2026 Akkana Peck

Pho is free software, licensed under the GNU Public License v. 2 or
(at your option) later GPL versions.

SEE ALSO
The most recent version of \fIpho\fR, and more information about it, is at:
https://github.com/akkana/metapho

More info is available at:
http://shallowsky.com/software/pho/
