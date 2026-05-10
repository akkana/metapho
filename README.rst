metapho
=======

An app for tagging and organizing large numbers of photos efficiently.

This arose out of my `Pho <http://shallowsky.com/software/pho/>`__ image
viewer (`Pho on GitHub <https://github.com/akkana/pho>`__), which was
starting to get unwieldy as I added ever more tagging features to what
was intended as just a fast, light image viewer. (Ironically, metapho
will eventually replace pho: the new Tk version of metapho includes a
tkpho image viewer script that’s intended to be feature-compatible with
pho, while the original pho will die once GTK2 ceases to be easily
available.)

Metapho is intended as a lightweight, flexible way of organizing large
numbers of photos. It uses text files, not a proprietary database, so
you’re not locked down to one app or a proprietary database, and you can
view your tags databases at any time, or edit them in a text editor.
Basically, you run it on a directory of images you’ve just uploaded:

::

   metapho *.jpg

and once you’ve tagged them all, it creates a file named *Tags*.

Metapho can be driven entirely from the keyboard: you should be able to
do everything you need without moving your hands to the mouse, though
you can use the mouse if you find that easier.

A Note about GTK vs. Tk
-----------------------

Historically, metapho has been built on GTK (currently GTK3), though it
never needed gnome or any other desktop services. But after trying to
port it to GTK4, I decided it would be easier to rewrite it in Tk, plus
it would be easier for people on non-Linux OSes. So metapho 2.0 will be
Tk based, without a GTK dependency.

I’ve been using tkpho and tkmetapho since January 2025 and it’s working
well. I plan to make Tk the default soon (written in April 2026).

Currently what metapho installs is:

-  metapho: GTK3-based metapho tagging app
-  gmetapho: GTK3-based metapho tagging app
-  tkmetapho: TkInter-based metapho tagging app
-  tkpho: TkInter-based pho image viewer

When 2.0 is released, metapho and pho will become the TkInter versions,
though gmetapho will still work if you have GTK3 libraries installed.

On Debian, you’ll need packages: python3-tk python3-pil
python3-pil.imagetk

Command-line Scripts
--------------------

Installing also gets you three command-line scripts:

| notags:
| Examine the current directory recursively and tell you about files and
  directories that still need to be tagged. Run it at the root of an
  image directory that might have untagged subdirectories.

| fotogr:
| Search for files with particular tags. For instance, ``fotogr cat``
  will print the names of all files you’ve tagged with “cat”.

| photoshare:
| Manage files tagged with “share” or “wallpaper”. See ``photoshare -h``
  for more info.

How to Install Metapho
----------------------

`Metapho is available on
PyPi <https://pypi.python.org/pypi/metapho/>`__, so you can install it
as ``pip install metapho`` (though of course the PyPI version won’t
always have the very latest features and bug fixes).

To install from the source directory, use ``pip install .``

The `Metapho
Documentation <https://metapho.readthedocs.io/en/latest/>`__ had more
information on both the app and the API of the classes inside it. Sadly,
this is now out of date because the tools I used to generate the
documentation no longer work, and porting the documentation to a
different system hasn’t been a high enough priority so far. However, the
existing documentation should still tell you most of what you need to
know about using the metapho app.
