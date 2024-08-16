metapho
=======

An app for tagging and organizing large numbers of photos efficiently.

This arose out of my [Pho](http://shallowsky.com/software/pho/)
image viewer ([Pho on GitHub](https://github.com/akkana/pho)).
It started to get unwieldy adding ever more tagging features to what
was intended as just a fast, light image viewer.

Metapho is intended as a lightweight, flexible way of organizing
large numbers of photos. It uses text files, not a proprietary database,
so you're not locked down to one app or a proprietary database,
and you can view your tags databases at any time, or edit them in a
text editor if you should ever want to.

Metapho can be driven entirely from the keyboard: you should be able
to do everything you need without moving your hands to the mouse,
though you can use the mouse if you find that easier.

It depends on PyGTK, but not on gnome or any other desktop services.

It also install three scripts:

notags:  
Examine the current directory recursively and tell you about files and
directories that still need to be tagged. Run it at the root of
an image directory that might have untagged subdirectories.

fotogr:  
Search for files with particular tags.

photoshare:  
Manage files tagged with "share".

[Metapho is available on PyPi](https://pypi.python.org/pypi/metapho/),
so you can install it as `pip install metapho`
(though of course the PyPI version won't always have the
very latest features and bug fixes).

Read the [Metapho Documentation](https://metapho.readthedocs.io/en/latest/)
for more information on both the app and the API of the classes
inside it.
