#!/usr/bin/env python3

# from . import ImageViewer
# from metapho.ImageViewer import PhoWidget

from ImageViewer import PhoImage, PhoWidget, VERBOSE

import tkinter as tk
import sys


class PhoWindow:
    def __init__(self, img_list=[], fixed_size=None):

        self.root = tk.Tk()

        self.root.title("Pho Image Viewer")

        # To allow resizing, set self.fixed_size to None
        if fixed_size:
            self.fixed_size = fixed_size
        else:
            self.fixed_size = None
        self.viewer = PhoWidget(self.root, img_list, size=self.fixed_size)

        self.root.bind('<Key-space>', self.image_nav_handler)
        self.root.bind('<Key-BackSpace>', self.image_nav_handler)
        self.root.bind('<Key-Home>', self.image_nav_handler)
        self.root.bind('<Key-End>', self.image_nav_handler)

        self.root.bind('<Key-Right>',
                       lambda e: self.rotate_handler(e, -90))
        self.root.bind('<Key-Left>',
                       lambda e: self.rotate_handler(e, 90))
        self.root.bind('<Key-Up>',
                       lambda e: self.rotate_handler(e, 180))
        self.root.bind('<Key-Down>',
                       lambda e: self.rotate_handler(e, 180))

        self.root.bind('<Key-f>', self.fullscreen_handler)
        self.root.bind('<Key-Escape>', self.fullscreen_handler)

        if self.fixed_size:
            # Allow the user to resize the window if it has a
            # fixed size. Otherwise, it will change with image size.
            self.root.bind("<Configure>", self.resize_handler)

        # Exit on either q or Ctrl-q
        self.root.bind('<Key-q>', self.quit_handler)
        self.root.bind('<Control-Key-q>', self.quit_handler)

    def run(self):
        self.viewer.next_image()
        self.root.mainloop()

    def add_image(img):
        self.viewer.add_image(img)

    def image_nav_handler(self, event):
        if event.keysym == 'space':
            self.viewer.next_image()
            return
        if event.keysym == 'BackSpace':
            self.viewer.prev_image()
            return
        if event.keysym == 'Home':
            self.viewer.goto_imageno(0)
            return
        if event.keysym == 'End':
            self.viewer.goto_imageno(-1)
            return

    def rotate_handler(self, event, rotation):
        self.viewer.rotate(rotation)

    def resize_handler(self, event):
        if (event.width, event.height) != self.fixed_size:
            if self.fixed_size:
                if VERBOSE:
                    print("Window resize! New size is",
                          event.width, event.height)
                self.fixed_size = (event.width, event.height)
                self.viewer.set_size(self.fixed_size)
                self.viewer.show_image()
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
            self.viewer.set_fullscreen(False)
            if VERBOSE:
                print("Out of fullscreen, fixed_size is", self.fixed_size)
 
        else:
            # Into fullscreen
            self.root.attributes("-fullscreen", True)
            if VERBOSE:
                print("Now in fullscreen, size", self.viewer.widget_size)
            self.viewer.fullscreen = True
            self.viewer.set_size((self.root.winfo_screenwidth(),
                                  self.root.winfo_screenheight()))

        # viewer.set_size() should redraw as necessary

    def quit_handler(self, event):
        if VERBOSE:
            print("Bye")
        sys.exit(0)


if __name__ == '__main__':
    import argparse
    import re

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

    if args.debug:
        VERBOSE = True

    if args.randomize:
        random.seed()
        args.images = random.shuffle(args.images)

    # The geometry argument is mostly for testing, to make sure
    # fixed size spaces like in metapho still work.
    win_width, win_height = 0, 0
    if args.geometry:
        try:
            win_size = list(map(int, re.match(r'([\d]+)x([\d]+)',
                                              args.geometry).groups()))
        except RuntimeError as e:
            win_size = None
            print("Couldn't parse geometry string '%s'" % args.geometry)

    pwin = PhoWindow(args.images, fixed_size=win_size)
    pwin.run()


