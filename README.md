metapho
=======

A keyboard-driven app for tagging and organizing large numbers of photos efficiently.

This arose out of my [Pho](http://shallowsky.com/software/pho/)
image viewer ([Pho on GitHub](https://github.com/akkana/pho)).
It started to get unwieldy adding ever more tagging features to what
was intended as just a fast, light image viewer.

Metapho is intended as a fast, lightweight, flexible way of organizing
large numbers of photos. It uses flat files, not a proprietary database,
so you're not locked down to one app or a proprietary database,
and you can view your tags databases at any time, or edit them in a
text editor if you should ever want to.

Metapho is driven primarily from the keyboard: you should be able to do
everything you need without moving your hands to the mouse, though
you can use the mouse if you find that easier.

It depends on PyGTK, but not on gnome or any other desktop services.
Linux users can get PyGTK and its dependencies through their distro
(e.g. apt-get install python-gtk2); Windows users can install it from pip.
I don't have a good answer for Mac users;
possibly the easiest solution is to install GIMP (follow the install
links from [GIMP.org](https://gimp.org) then fiddle with paths
so that other programs can find the PyGTK libraries that comes with GIMP.

[Metapho is available on PyPi](https://pypi.python.org/pypi/metapho/),
so you can install it as
`[pip install metapho]`.

Read the [Metapho Documentation](http://pythonhosted.org/metapho/)
for more information on either the app and on the API of the classes
inside it.
