#!/usr/bin/env python3

from .tkPhoImage import tkPhoImage
from .tkPhoWidget import tkPhoWidget, VERBOSE

import tkinter as tk
# You can't just use tk.messagebox, apparently
from tkinter import messagebox, Toplevel

import random
import sys, os


class tkPhoWindow (Toplevel):
    """The main window for tkPho.
       Shows a tkPhoWidget and has bindings to let the user move
       through the image list, rotate, zoom, delete, etc.
    """

    def __init__(self, img_list=[], fixed_size=None, fullscreen=None):
        if fullscreen is None:
            fullscreen = False

        self.full_size = False

        self.root = tk.Tk()

        self.root.title("Pho Image Viewer")

        # To allow resizing, set self.fixed_size to None
        if fixed_size:
            self.fixed_size = fixed_size
        else:
            self.fixed_size = None
        self.pho_widget = tkPhoWidget(self.root, img_list, size=self.fixed_size)

        # Middlemouse drag is only needed when fullscreen AND fullsize
        self.dragging_from = None

        # List of Tk keysyms:
        # https://www.tcl.tk/man/tcl8.4/TkCmd/keysyms.htm
        # https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/key-names.html

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

        self.root.bind("<ButtonPress-2>",   self.start_drag)
        self.root.bind("<B2-Motion>",       self.drag)
        self.root.bind("<ButtonRelease-2>", self.end_drag)

        # self.root.bind("<ButtonPress-2>", lambda x: print("2 PRESS"))
        # self.root.bind("<ButtonRelease-2>", lambda x: print("2 RELEASE"))
        # self.root.bind("<B2-Motion>", lambda x: print("2 MOTION"))

        for i in range(10):
            self.root.bind('<Key-%d>' % i, self.digit_handler)

        # p (presentation) toggles fullscreen mode;
        # ESC always exits it.
        self.root.bind('<Key-p>', self.fullscreen_handler)
        self.root.bind('<Key-Escape>', self.fullscreen_handler)

        # f toggles full-size mode
        self.root.bind('<Key-f>', self.fullsize_handler)

        self.root.bind('<Key-d>', self.delete_handler)


        if self.fixed_size:
            # Allow the user to resize the window if it has a
            # fixed size. Otherwise, it will change with image size.
            self.root.bind("<Configure>", self.resize_handler)

        # Exit on either q or Ctrl-q
        self.root.bind('<Key-q>', self.quit)
        self.root.bind('<Control-Key-q>', self.quit)

        if fullscreen:
            self.go_fullscreen(True)

    def run(self):
        try:
            self.pho_widget.next_image()
            self.update_title()
        except Exception as e:
            print(e)
            sys.exit(1)
        self.root.mainloop()

    def add_image(img):
        self.pho_widget.add_image(img)

    def image_nav_handler(self, event):
        # print("geometry now is %dx%d+%d+%d" % (self.root.winfo_x(),
        #                                        self.root.winfo_y(),
        #                                        self.root.winfo_width(),
        #                                        self.root.winfo_height()))
        try:
            if event.keysym == 'space' or event.keysym == 'Next':
                self.pho_widget.next_image()
            if event.keysym == 'BackSpace' or event.keysym == 'Prior':
                self.pho_widget.prev_image()
            if event.keysym == 'Home':
                self.pho_widget.goto_imageno(0)
            if event.keysym == 'End':
                self.pho_widget.goto_imageno(-1)
        except FileNotFoundError as e:
            print(e)
            # FileNotFoundError only happens if none of the specified
            # images are viewable.
            self.quit()
        except IndexError as e:
            # Can't go beyond last image.
            ans = messagebox.askyesno("Last Image",
                                      "Last image: quit?")
            # This will be true if the user said yes, quit
            if ans:
                self.quit()

        self.update_title()

    def update_title(self):
        self.root.title(f"Pho: {self.pho_widget.current_image().relpath}")

    def digit_handler(self, event):
        self.pho_widget.current_image().add_tag(event.keysym)

    def rotate_handler(self, event, rotation):
        self.pho_widget.rotate(rotation)
        self.pho_widget.show_image()

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
        """f toggles, ESC gets out of fullscreen.
        """
        # Escape should always exit fullscreen
        if event.keysym == 'Escape':
            return self.go_fullscreen(False)

        # Else toggle
        if (self.root.attributes('-fullscreen')):  # already fullscreen
            return self.go_fullscreen(False)

        else:
            return self.go_fullscreen(True)

    def go_fullscreen(self, fullscreen_on):
        """fullscreen_on==True -> go to fullscreen
           fullscreen_on==False -> out of fullscreen
           fullscreen_on==None -> toggle
        """
        if fullscreen_on:
            # Into fullscreen
            self.root.attributes("-fullscreen", True)
            if VERBOSE:
                print("Now in fullscreen, size", self.pho_widget.widget_size)
            self.pho_widget.fullscreen = True
            self.pho_widget.set_size((self.root.winfo_screenwidth(),
                                      self.root.winfo_screenheight()))

            # if self.pho_widget.fullsize:
            #     self.pho_widget.center_fullsize()

            # enable middlemouse dragging
            # https://tkinterexamples.com/events/mouse/
            self.root.bind("ButtonPress-2", self.start_drag)
            self.root.bind("<B2-Motion>", self.drag)
            self.root.bind("ButtonRelease-2", self.end_drag)
        else:
            self.root.attributes("-fullscreen", False)
            # Sadly, the viewer widget can't just check the root attributes
            # before set_size(), because the root attribute won't actually
            # change until later, so now, it will still show as True.
            self.pho_widget.set_fullscreen(False)
            if VERBOSE:
                print("Out of fullscreen, fixed_size is", self.fixed_size)

            # disable middlemouse dragging
            # self.root.bind("<B2-Motion>", None)
            self.root.unbind("<B2-Motion>")

        # viewer.set_size() should redraw as necessary

    def fullsize_handler(self, event):
        if self.fixed_size:
            if VERBOSE:
                print("full-size mode not supported in a fixed-size window")
            return
        self.pho_widget.fullsize = not self.pho_widget.fullsize
        self.pho_widget.show_image()

        # Going from fullsize to normal, it's all too easy
        # to end up with the window mostly off the screen.
        # So make sure the upper left corner is on-screen.
        # print("Window position now:",
        #       self.root.winfo_x(), self.root.winfo_y(),
        #       self.root.winfo_width(), self.root.winfo_height())
        if self.root.winfo_x() < 0 or self.root.winfo_y() < 0:
            self.root.geometry("+100+100")

    def start_drag(self, event):
        self.dragging_from = event.x_root, event.y_root

    def drag(self, event):
        if not self.pho_widget.fullscreen or not self.pho_widget.fullsize:
            print("Can't drag except in fullsize+fullscreen mode")
            return
        if not self.dragging_from:
            print("drag without start_drag")
            return

        # event.x_root is the coordinate relative to the screen,
        # event.x is relative to the window.
        # Sure would be nice if TkInter had documentation somewhere.

        # print("ddddddddddddddrag",
        #       "    dragging_from:", self.dragging_from,
        #       "    xy_root:", event.x_root, event.y_root,
        #       "    xy:", event.x, event.y,
        #       "    -->", event.x_root - self.dragging_from[0],
        #       event.y_root - self.dragging_from[1])

        self.pho_widget.translate(event.x_root - self.dragging_from[0],
                                  event.y_root - self.dragging_from[1])
        self.dragging_from = (event.x_root, event.y_root)

        self.pho_widget.show_image()

    def end_drag(self, event):
        self.dragging_from = None

    def delete_handler(self, event):
        # To bind 'd' in the dialog, we'll probably need to replace the
        # messagebox with a custom dialog, like
        # https://stackoverflow.com/a/48324446
        # https://stackoverflow.com/a/10065345
        ans = messagebox.askyesno("Delete", "Really delete?")
        # XXX how to intercept a typed 'd' in this dialog?
        if ans:
            self.pho_widget.delete_current()

    def quit(self, event=None):
        if VERBOSE:
            print("Bye")

        # Print any tags that were set
        tagged = tkPhoImage.tagged_images()
        for tag in tagged:
            print("%s: %s" % (tag, ' '.join([img.relpath
                                             for img in tagged[tag]])))

        sys.exit(0)


def main():
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
    parser.add_argument('-p', "--presentation", dest="presentation",
                        default=False, action="store_true",
                        help="Presentation mode (full screen, centered)")
    parser.add_argument('-P', "--nopresentation", dest="nopresentation",
                        default=False, action="store_true",
                        help="NOT presentation mode")
    parser.add_argument('-R', "--randomize", dest="randomize", default=False,
                        action="store_true",
                        help="Present images in random order")
    parser.add_argument('-v', "--verbosehelp", dest="verbosehelp",
                        default=False,
                        action="store_true", help="Print verbose help")
    parser.add_argument("--geometry", dest="geometry", action="store",
                        help="A geometry size string, WIDTHxHEIGHT "
                             "(sorry, no x and y position)")
    parser.add_argument('-d', "--debug", dest="debug", default=False,
                        action="store_true", help="Print debugging messages")
    parser.add_argument('images', nargs='+', help="Images to show")

    # Also look at PHO_ARGS environment variable
    try:
        envargs = os.getenv('PHO_ARGS').split()
        argv = envargs + sys.argv[1:]
    except:
        argv = sys.argv[1:]

    args = parser.parse_args(argv)

    # This doesn't work: it sets a file-local VERBOSE rather than
    # changing the one imported from tkPhoWidget
    if args.debug:
        VERBOSE = True

    if args.nopresentation:
        args.presentation = False

    if args.randomize:
        random.seed()
        random.shuffle(args.images)

    # The geometry argument is mostly for testing, to make sure
    # fixed size spaces like in metapho still work.
    win_size = None
    if args.geometry:
        try:
            win_size = list(map(int, re.match(r'([\d]+)x([\d]+)',
                                              args.geometry).groups()))
        except RuntimeError as e:
            print("Couldn't parse geometry string '%s'" % args.geometry)

    pwin = tkPhoWindow(args.images, fixed_size=win_size,
                       fullscreen=args.presentation)
    pwin.run()


if __name__ == '__main__':
    main()
