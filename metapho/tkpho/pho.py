#!/usr/bin/env python3

# from . import ImageViewer
# from metapho.ImageViewer import PhoWidget

from PhoWidget import PhoImage, PhoWidget, VERBOSE

import tkinter as tk
# You can't just use tk.messagebox, apparently
from tkinter import messagebox
import sys


class PhoWindow:
    def __init__(self, img_list=[], fixed_size=None):
        self.full_size = False

        self.root = tk.Tk()

        self.root.title("Pho Image Viewer")

        # To allow resizing, set self.fixed_size to None
        if fixed_size:
            self.fixed_size = fixed_size
        else:
            self.fixed_size = None
        self.pho_widget = PhoWidget(self.root, img_list, size=self.fixed_size)

        # List of Tk keysyms:
        # https://www.tcl.tk/man/tcl8.4/TkCmd/keysyms.htm

        self.root.bind('<Key-space>', self.image_nav_handler)
        self.root.bind('<Key-BackSpace>', self.image_nav_handler)
        self.root.bind('<Key-Home>', self.image_nav_handler)
        self.root.bind('<Key-End>', self.image_nav_handler)
        # "Prior" and "Next" are Tk-ese for page up/down
        self.root.bind('<Key-Prior>', self.image_nav_handler)
        self.root.bind('<Key-Next>', self.image_nav_handler)

        self.root.bind('<Key-Right>',
                       lambda e: self.rotate_handler(e, -90))
        self.root.bind('<Key-Left>',
                       lambda e: self.rotate_handler(e, 90))
        self.root.bind('<Key-Up>',
                       lambda e: self.rotate_handler(e, 180))
        self.root.bind('<Key-Down>',
                       lambda e: self.rotate_handler(e, 180))

        # p (presentation) toggles fullscreen mode;
        # ESC always exits it.
        self.root.bind('<Key-p>', self.fullscreen_handler)
        self.root.bind('<Key-Escape>', self.fullscreen_handler)

        # f toggles full-size mode
        self.root.bind('<Key-f>', self.fullsize_handler)

        if self.fixed_size:
            # Allow the user to resize the window if it has a
            # fixed size. Otherwise, it will change with image size.
            self.root.bind("<Configure>", self.resize_handler)

        # Exit on either q or Ctrl-q
        self.root.bind('<Key-q>', self.quit_handler)
        self.root.bind('<Control-Key-q>', self.quit_handler)

    def run(self):
        try:
            self.pho_widget.next_image()
        except Exception as e:
            print(e)
            sys.exit(1)
        self.root.mainloop()

    def add_image(img):
        self.pho_widget.add_image(img)

    def image_nav_handler(self, event):
        try:
            if event.keysym == 'space' or event.keysym == 'Next':
                self.pho_widget.next_image()
                return
            if event.keysym == 'BackSpace' or event.keysym == 'Prior':
                self.pho_widget.prev_image()
                return
            if event.keysym == 'Home':
                self.pho_widget.goto_imageno(0)
                return
            if event.keysym == 'End':
                self.pho_widget.goto_imageno(-1)
                return
        except FileNotFoundError as e:
            print(e)
            # FileNotFoundError only happens if none of the specified
            # images are viewable.
            sys.exit(1)
        except IndexError as e:
            # Can't go beyond last image.
            ans = messagebox.askyesno("Last Image",
                                      "Last image: quit?")
            # This will be true if the user said yes, quit
            if ans:
                sys.exit(0)

    def rotate_handler(self, event, rotation):
        self.pho_widget.rotate(rotation)

    def resize_handler(self, event):
        if (event.width, event.height) != self.fixed_size:
            if self.fixed_size:
                if VERBOSE:
                    print("Window resize! New size is",
                          event.width, event.height)
                self.fixed_size = (event.width, event.height)
                self.pho_widget.set_size(self.fixed_size)
                self.pho_widget.show_image()
            elif VERBOSE:
               print("Resize event, but who cares?")

    def fullscreen_handler(self, event):
        """f toggles, ESC gets out of fullscreen"""
        # Escape should always exit fullscreen
        if (event.keysym == 'Escape' or
            self.root.attributes('-fullscreen')):  # already fullscreen
            self.root.attributes("-fullscreen", False)
            # Sadly, the viewer widget can't just check the root attributes
            # before set_size(), because the root attribute won't actually
            # change until later, so now, it will still show as True.
            self.pho_widget.set_fullscreen(False)
            if VERBOSE:
                print("Out of fullscreen, fixed_size is", self.fixed_size)
 
        else:
            # Into fullscreen
            self.root.attributes("-fullscreen", True)
            if VERBOSE:
                print("Now in fullscreen, size", self.pho_widget.widget_size)
            self.pho_widget.fullscreen = True
            self.pho_widget.set_size((self.root.winfo_screenwidth(),
                                  self.root.winfo_screenheight()))

        # viewer.set_size() should redraw as necessary

    def fullsize_handler(self, event):
        if self.fixed_size:
            if VERBOSE:
                print("full-size mode not supported in a fixed-size window")
            return
        self.pho_widget.fullsize = not self.pho_widget.fullsize
        print("fullsize now", self.pho_widget.fullsize)
        print("VERBOSE from pho.py:", VERBOSE)
        self.pho_widget.show_image()

        # Going from fullsize to normal, it's all too easy
        # to end up with the window mostly off the screen.
        # So make sure the upper left corner is on-screen.
        # print("Window position now:",
        #       self.root.winfo_x(), self.root.winfo_y(),
        #       self.root.winfo_width(), self.root.winfo_height())
        if self.root.winfo_x() < 0 or self.root.winfo_y() < 0:
            self.root.geometry("+100+100")

    def quit_handler(self, event):
        if VERBOSE:
            print("Bye")
        sys.exit(0)


if __name__ == '__main__':
    import argparse
    import re

    verbose_help = """
pho Key Bindings:

<space>, <Page Down>
	Next image (or cancel slideshow mode)
<backspace>, <Page Up>
	Previous image
<home>	First image
<end>	Last image
p	Toggle presentation mode (take up the whole screen, centering the image)
f	Toggle full-size mode (even if bigger than screen)

d	Delete current image (from disk, after confirming with another d)

0-9	Remember image in note list 0 through 9 (to be printed at exit)
	(In keywords dialog, alt + 0-9 adds 10, e.g. alt-4 triggers flag 14.

<Right>	Rotate right 90 degrees
<Left>]	Rotate left 90 degrees
<up>	Rotate 180 degrees

+, =	Double size
/, -	Half size

i	Show/hide info dialog
k	Turn on keywords mode: show the keywords dialog
o	Change the working file set (add files or make a new list)
g	Run gimp on the current image
	(or set PHO_CMD to an alternate command)
q	Quit
<esc>	Quit (or hide a dialog, if one is showing)

Pho mouse bindings:
In presentation mode: drag with middlemouse to pan/move.

Pho environment variables:
PHO_ARGS: default arguments (e.g. -p)
PHO_CMD : command to run when pressing g (default: gimp).
          Use an empty string if you don't want any command.
"""

    parser = argparse.ArgumentParser(
        description="Pho, an image viewer and tagger")
    parser.add_argument('-d', "--debug", dest="debug", default=False,
                        action="store_true", help="Print debugging messages")
    parser.add_argument('-R', "--randomize", dest="randomize", default=False,
                        action="store_true",
                        help="Present images in random order")
    parser.add_argument('-v', "--verbosehelp", dest="verbosehelp",
                        default=False,
                        action="store_true", help="Print verbose help")
    parser.add_argument("--geometry", dest="geometry", action="store",
                        help="A geometry size string, WIDTHxHEIGHT "
                             "(sorry, no x and y position)")
    parser.add_argument('images', nargs='+', help="Images to show")
    args = parser.parse_args(sys.argv[1:])

    # This doesn't work: it sets a file-local VERBOSE rather than
    # changing the one imported from PhoWidget
    if args.debug:
        VERBOSE = True

    if args.randomize:
        random.seed()
        args.images = random.shuffle(args.images)

    # The geometry argument is mostly for testing, to make sure
    # fixed size spaces like in metapho still work.
    win_size = None
    if args.geometry:
        try:
            win_size = list(map(int, re.match(r'([\d]+)x([\d]+)',
                                              args.geometry).groups()))
        except RuntimeError as e:
            print("Couldn't parse geometry string '%s'" % args.geometry)

    pwin = PhoWindow(args.images, fixed_size=win_size)
    pwin.run()


