#!/usr/bin/env python3

"""A TkInter Image Viewer.
   Suitable for embedding in larger apps, or use it by itself
   as a standalone image viewer.

   Copyright 2024 by Akkana -- Share and enjoy under the GPLv2 or later.
"""

import sys, os

import tkinter as tk
from PIL import Image as PILImage
from PIL import ImageTk, ExifTags, UnidentifiedImageError

from metapho import MetaphoImage, g_image_list

VERBOSE = False

FRAC_OF_SCREEN = .85

# The numeric key where EXIF orientation is stored.
# None means it hasn't been initialized yet;
# -1 means there was an error initializing, so EXIF orientation won't work.
EXIF_ORIENTATION_KEY = None


def get_screen_size(root):
    return root.winfo_screenwidth(), root.winfo_screenheight()


class PhoImage (MetaphoImage):
    """An image object that saves an original PILImage object
       read in from disk, some state such as rotation,
       possibly a scaled and rotated display PILImage.
       It also knows how to get quantities like size and EXIF rotation.
       And it has tagging attributes since it inherits from MetaphoImage,
       and can be used in the metapho g_image_list.
    """

    INVALID = "Invalid Image"

    def __init__(self, filename):
        MetaphoImage.__init__(self, filename)

        # self.rot is initialized by MetaphoImage,
        # but it doesn't handle EXIF
        self.exif_rotation = 0

        # The original image as loaded from the file path.
        # This is never rotated.
        self.orig_img = None

        # Image as currently displayed: rotated and scaled
        self.display_img = None

        # If the image couldn't be loaded, an error string is here:
        errstr = None

    def __repr__(self):
        extra = ''
        if self.orig_img:
            extra += ' orig %dx%d' % self.orig_img.size
        if self.display_img:
            extra += ' displayed %dx%d' % self.display_img.size
        return f'<PhoImage {self.relpath}{extra}>'

    # Properties
    def get_size(self):
        if self.display_img:
            return self.display_img.size
        return self.orig_img.size

    size = property(get_size)
    # End Properties

    def load(self):
        """Make sure the image is loaded. May raise FileNotFoundError
           or UnidentifiedImageError.
        """
        # Don't reload if self.orig_img is already there
        if self.orig_img:
            return
        VERBOSE = True
        try:
            self.orig_img = PILImage.open(self.relpath)
            self.rot = self.get_exif_rotation()
            self.display_img = None

        except Exception as e:
            self.orig_img = None
            self.display_img = None
            raise e

    def rotate(self, degrees):
        if VERBOSE:
            print("Rotating", degrees, "starting from", self.rot,
                  "-->", self.rot + degrees)
        self.rot = (self.rot + degrees) % 360

        if degrees % 180:
            # If changing aspect ratio, we'll need a new display_img.
            # Clear it, and a new one will be generated by resize_to_fit.
            self.display_img = None

        elif degrees == 180:
            # Rotating without changing aspect ratio:
            # rotate the display_img since size won't change.
            # This could be extra work if we have to do it again.
            # but it could also save work scaling down from the original.
            # XXX Check this.
            if self.display_img:
                self.display_img = self.display_img.rotate(180)
            # self.display_img = None

    def get_exif_rotation(self):
        global EXIF_ORIENTATION_KEY
        # EXIF_ORIENTATION_KEY is currently 274, but don't count on that.
        if EXIF_ORIENTATION_KEY is None:
            EXIF_ORIENTATION_KEY = -1
            for k in ExifTags.TAGS.keys():
                if ExifTags.TAGS[k] == 'Orientation':
                    EXIF_ORIENTATION_KEY = k
                    break
        if EXIF_ORIENTATION_KEY < 0:
            print("Internal error: can't read any EXIF")
            self.exif_rotation = 0
            return 0

        exif = self.orig_img.getexif()
        try:
            if exif[EXIF_ORIENTATION_KEY] == 3:
                self.exif_rotation = 180
            elif exif[EXIF_ORIENTATION_KEY] == 6:
                self.exif_rotation = -90
            elif exif[EXIF_ORIENTATION_KEY] == 8:
                self.exif_rotation = 90
            if VERBOSE:
                print("EXIF rotation is", self.exif_rotation)
            return self.exif_rotation
        except Exception as e:
            if VERBOSE:
                print("Problem reading EXIF rotation", file=sys.stderr)
            return self.exif_rotation

    def resize_to_fit(self, bbox):
        """Ensure that display_img, as rotated and scaled, fits in the
           bbox (width, height), reloading from orig_img if needed.
           Return self.display_img, a PILImage.
        """
        if not self.orig_img:
            self.load()

        # Is there already a display_image of the correct size?
        # That means one dimension should match the bbox, the other is <=
        if self.display_img:
            dw, dh = self.display_img.size
            if ((dw == bbox[0] and dh <= bbox[1]) or
                (dw <= bbox[0] and dh == bbox[1])):
                if VERBOSE:
                    print("display image is already scaled to the window")
                return self.display_img

        # What are the original dimensions, taking rotation into account?
        # (orig_img is not rotated, display_img is)
        if self.rot % 90:
            oh, ow = self.orig_img.size
        else:
            ow, oh = self.orig_img.size

        # Would the original image fit in the bbox?
        if ow <= bbox[0] and oh <= bbox[1]:
            # It would fit. Is there already a display image that size?
            if self.display_img and self.display_img.size == (ow, oh):
                if VERBOSE:
                    print("display image is already small enough")
                return self.display_img
            # Nope. So create a new display_img, possibly rotated
            if self.rot % 90:
                self.display_img = self.orig_img.rotate(self.rot)
            else:
                self.display_img = self.orig_img
            return self.display_img

        # display_img is bigger than the bbox.
        # Need to scale down from orig_img, which may first involve rotating it
        if self.rot % 180:
            self.display_img = self.orig_img.rotate(self.rot, expand=True)
        elif self.rot:
            self.display_img = self.orig_img.rotate(self.rot, expand=True)
        else:
            self.display_img = self.orig_img

        # Now resize it to fit:
        if VERBOSE:
            print("Resizing to fit in %dx%d" % bbox)
        wratio = self.display_img.size[0] / bbox[0]
        hratio = self.display_img.size[1] / bbox[1]
        ratio = max(wratio, hratio)
        dw, dh = self.display_img.size
        self.display_img = self.display_img.resize(size=(int(dw / ratio),
                                                         int(dh / ratio)))
        if VERBOSE:
            print("Resized to", self.display_img.size)

        return self.display_img


class PhoWidget:
    """An object that can be displayed inside a window
       and holds an image list.
       It can move forward (next) and back (previous) through the list,
       properly scale and rotate images to fit the available space,
       plus a few other functions like deleting the image file.
    """

    def __init__(self, parent, img_list=None, size=None):
        """img_list is a list of image path strings.
           If size is omitted, the widget will be free to resize itself,
           otherwise it will try to fit itself in the space available.
        """
        if not img_list:
            img_list = []
        # Trying to treat metapho.g_image_list like a global
        # doesn't work; need to make sure the g_image_list used is
        # the one from base metapho, not a new one created here.
        g_image_list.extend([ PhoImage(f) for f in img_list ])

        self.imgno = -1

        self.root = parent    # Needed for queries like screen size

        self.fixed_size = size
        self.widget_size = size
        self.fullscreen = False

        # In fullsize mode, the whole image will be displayed
        # even if it's too big to fit on screen.
        self.fullsize = False

        # In fullsize + fullscreen mode, images will be initially centered,
        # but the user can drag with the middle button to change the offset.
        # Only applies to the current image, reset when changing images.
        self.fullsize_offset = 0, 0

        # The actual widget where images will be shown.
        # It would be nice to set the widget size here if size is fixed,
        # but width and height passed in a Label constructor are interpreted
        # as number of characters, not pixels, and there's apparently
        # no way to specify size in pixels.
        # (You can specify pixel size for ImageTk.PhotoImage.resize()
        # but for that, you have to have an image ready to show.)
        if size:
            self.lwidget = tk.Label(parent, width=size[0], height=size[1],
                                    padx=0, pady=0)
            self.lwidget.pack(fill="both", expand=False, padx=0, pady=0)
        else:
            self.lwidget = tk.Label(parent)
            self.lwidget.pack(fill="both", expand=True, padx=0, pady=0)

        self.lwidget.configure(background='black')

    def current_image(self):
        """Returns a PhoImage"""
        return g_image_list[self.imgno]

    def add_image(self, imgpath):
        """Add an image to the image list.
        """
        g_image_list.append(PhoImage(imgpath))

    def get_widget_size(self):
        return (self.lwidget.winfo_width(),
                self.lwidget.winfo_height())

    def set_fullscreen(self, state):
        self.fullscreen = state
        if state:
            self.set_size(get_screen_size())
        elif self.fixed_size:
            self.widget_size = self.fixed_size
        else:
            self.widget_size = self.get_widget_size()

    def set_size(self, newsize):
        """Change the size of the widget.
           Since this comes from callers outside the widget,
           allow it to override self.fixed_size.
        """
        if VERBOSE:
            print("PhoWidget set_size", newsize)

        if not newsize and not self.widget_size:
            self.widget_size = self.get_widget_size()
            if VERBOSE:
                print("Actual widget size:", self.widget_size)

        # This can be called many times, so don't do anything
        # if nothing changed since last time.
        elif newsize == self.widget_size:
            return

        self.widget_size = newsize

        self.show_image()

    def show_image(self):
        """Show the current image.
           Return 1 for success, 0 for valid image but not ready,
           -1 for invalid image or other error.
        """
        if VERBOSE:
            print("PhoWidget.show_image, widget size is", self.widget_size)

        try:
            pil_img = self.resize_to_fit()
        except (FileNotFoundError, UnidentifiedImageError) as e:
            # Any exception means it's not a valid image and should
            # be removed from the list.
            print("Eek, don't know how to handle an exception in show_image",
                  file=sys.stderr)
            print("Exception was:", e)
            return
        if not pil_img:
            print("Eek, resize_to_fit didn't return an image!", file=sys.stderr)
            return

        tkimg = ImageTk.PhotoImage(pil_img)
        self.lwidget.config(image=tkimg)
        self.lwidget.photo = tkimg

        # At this point,
        # self.lwidget.winfo_reqwidth(), self.lwidget.winfo_reqheight()
        # should be the size of the image,
        # though in practice it adds 2 pixels to both height and width.
        # self.lwidget.winfo_width(), self.lwidget.winfo_height()
        # is the size of the previous image, i.e. the current widget size,
        # except at the beginning where it's 1, 1

    def resize_to_fit(self):
        """Resize the current image to fit in the current widget.
           but no larger than the bbox (width, height)
           (except in fullsize mode, where it translates as needed).
           Also rotate if needed.

           Return self.display_img, a PIL Image ready to display.
        """
        if VERBOSE:
            print("resize_to_fit")
        cur_img = g_image_list[self.imgno]
        if self.fullsize and self.fullscreen:
            if cur_img.display_img and (self.fullsize_offset[0]
                                        or self.fullsize_offset[1]):
                # there's an offset, so don't center.
                # The user has already dragged, so keep display_img
                if VERBOSE:
                    return cur_img.display_img

            # in both fullsize and fullscreen mode, initially center the image
            if cur_img.rot:
                cur_img.display_img = \
                    cur_img.orig_img.rotate(cur_img.rot)
                cur_img.display_img = \
                    self.center_fullsize(cur_img.orif_img)
            else:
                cur_img.display_img = \
                    self.center_fullsize(cur_img.orig_img)
            return cur_img.display_img

        elif self.fullsize:
            target_size = cur_img.orig_img.size
            if VERBOSE:
                print("resize_to_fit in fullsize mode", target_size)

        elif self.fullscreen:
            target_size = get_screen_size(self.root)
            if VERBOSE:
                print("resize_to_fit, fullscreen,", target_size)

        elif not self.fixed_size:                  # resizable
            if VERBOSE:
                print("Resizable widget")
            target_size = (self.root.winfo_screenwidth() * FRAC_OF_SCREEN,
                           self.root.winfo_screenheight() * FRAC_OF_SCREEN)
            if VERBOSE:
                print("resize_to_fit, variable height ->", target_size)

        else:                                      # fixed-size window
            target_size = self.widget_size
            if VERBOSE:
                print("resize_to_fit, fixed at", target_size)

        if VERBOSE:
            print("Target space:", target_size)

        return cur_img.resize_to_fit(target_size)

    def translate(self, dx, dy):
        # print("PhoWidget.translate", dx, dy, "->",
        #       self.fullsize_offset, end='')
        self.fullsize_offset = (self.fullsize_offset[0] + dx,
                                self.fullsize_offset[1] + dy)
        # print(" ->", self.fullsize_offset)
        g_image_list[self.imgno].display_img = None

    def center_fullsize(self, pil_img):
        """translate the given pil_img, assumed to be larger than the
           widget size, so that it's centered in the available space.
           Shift it by self.fullsize_offset, set from user mouse drags.

           Return the translated pil_img.
        """
        # when in both fullscreen and fullsize, it's best to start
        # with the center of the image centered on the screen
        iw, ih = pil_img.size
        if VERBOSE:
            print("center_fullsize: transforming",
                  int((iw - self.root.winfo_screenwidth())/2),
                  int((ih - self.root.winfo_screenheight())/2))

        return pil_img.transform(pil_img.size, Image.AFFINE,
                                 (1, 0,
                                  int((iw - self.root.winfo_screenwidth())/2) - self.fullsize_offset[0],
                                  0, 1,
                                  int((ih - self.root.winfo_screenheight())/2 - self.fullsize_offset[1])))
        # then crop, https://stackoverflow.com/a/44684388
        # but that doesn't seem to be needed.
        # Is there any point to cropping off the extra lower right parts?
        # new_size = (g_image_list[self.imgno].display_img.size[0] - dx,
        #             g_image_list[self.imgno].display_img.size[1] - dy)
        # return cur_img.display_img.transform(
        #         new_size, Image.EXTENT, (0, 0, new_size[0], new_size[1]))

    def rotate(self, rotation):
        g_image_list[self.imgno].rotate(rotation)

    def delete_current(self):
        # Remove from the img_list
        deleted = g_image_list.pop(self.imgno)

        # delete the file on disk
        os.unlink(deleted.filename)

        self.show_image()

    def next_image(self):
        if not g_image_list:
            raise FileNotFoundError("No image list!")

        self.imgno += 1

        while True:
            if self.imgno >= len(g_image_list):
                self.imgno = len(g_image_list) - 1
                if VERBOSE:
                    print("Can't go beyond last image")
                # Special case: if none of the images are viewable,
                # we'll get here without anything to show.
                if not g_image_list:
                    raise FileNotFoundError("Couldn't show any of the images")

                raise IndexError("Can't go beyond last image")

            # Is the current image valid?
            try:
                g_image_list[self.imgno].load()

            except (FileNotFoundError, UnidentifiedImageError,
                    IsADirectoryError, AttributeError) as e:
                print("Skipping", g_image_list[self.imgno].relpath,
                      "because:", e)
                # PIL prints its errors with full paths, even if it was
                # a relative path passed in. I wish I could shorten them.
                del g_image_list[self.imgno]
                continue
            except Exception as e:
                print("Skipping an image for an unexpected reason:", type(e),
                      g_image_list[self.imgno])
                del g_image_list[self.imgno]
                continue

            # Whew, load() worked okay, the image is valid
            if VERBOSE:
                print("  to", self.imgno, "->", g_image_list[self.imgno])

            self.fullsize_offset = 0, 0
            self.show_image()
            return

    def prev_image(self):
        if not g_image_list:
            raise FileNotFoundError("No image list!")

        while True:
            self.imgno -= 1
            if self.imgno < 0:
                self.imgno = 0
                if VERBOSE:
                    print("Can't look before first image")
                    return

            # Is the current image valid?
            try:
                g_image_list[self.imgno].load()
            except (FileNotFoundError, UnidentifiedImageError) as e:
                print("Skipping", g_image_list[self.imgno], e)
                del g_image_list[self.imgno]
                continue

            # Whew, load() worked okay, the image is valid
            if VERBOSE:
                print("  to", self.imgno, "->", g_image_list[self.imgno])

            self.fullsize_offset = 0, 0
            self.show_image()
            return

    def goto_imageno(self, imagenum):
        num_images = len(g_image_list)
        if imagenum >= num_images:
            self.imgno = num_images()
            self.prev_image()
            return
        if imagenum < 0:
            # For negative numbers, count back, -1 being the last image
            self.imgno = num_images - imagenum - 1
            self.prev_image()
            return
        self.imgno = imagenum - 1
        self.fullsize_offset = 0, 0
        self.next_image()
        return


class SimpleImageViewerWindow:
    """A simple example of how to use PhoWidget
    """
    def __init__(self, img_list=[], fixed_size=None):

        self.root = tk.Tk()

        self.root.title("Metapho Image Viewer")

        # To allow resizing, set self.fixed_size to None
        if fixed_size:
            self.fixed_size = fixed_size
        else:
            self.fixed_size = None
        self.viewer = PhoWidget(self.root, img_list,
                                size=self.fixed_size)
        self.root.bind('<Key-space>', self.image_nav_handler)
        self.root.bind('<Key-BackSpace>', self.image_nav_handler)
        self.root.bind('<Key-Home>', self.image_nav_handler)
        self.root.bind('<Key-End>', self.image_nav_handler)

        # Exit on Ctrl-q
        self.root.bind('<Control-Key-q>', self.quit_handler)

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

    def run(self):
        self.viewer.next_image()
        self.root.mainloop()

    def quit_handler(self, event):
        if VERBOSE:
            print("Bye")
        sys.exit(0)


if __name__ == '__main__':
    win = SimpleImageViewerWindow(sys.argv[1:], fixed_size=None)
    win.run()

