#!/usr/bin/env python3

"""A TkInter Image Viewer.
   Suitable for embedding in larger apps, or use it by itself
   as a standalone image viewer.

   Copyright 2024,2025,2026 by Akkana -- Share and enjoy under the GPLv2 or later.
"""


from metapho import MetaphoImage, imagelist

# This works when running the installed app, but not when running ./tkPhoWidget
from .tk_pho_image import tkPhoImage
# But to get VERBOSE, we need to refer to it explicitly as tk_pho_image.VERBOSE
from . import tk_pho_image

import tkinter as tk
from PIL import Image as PILImage
from PIL import ImageTk, ExifTags, UnidentifiedImageError

import sys, os


FRAC_OF_SCREEN = .85


def get_screen_size(root):
    return root.winfo_screenwidth(), root.winfo_screenheight()


class tkPhoWidget (tk.Label):
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
        self.root = parent    # Needed for queries like screen size

        self.fixed_size = size
        self.widget_size = size
        self.fullscreen = False

        self.scale_factor = 1.0

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
            super().__init__(parent, width=size[0], height=size[1],
                             padx=0, pady=0)
            self.pack(fill="both", expand=False, padx=0, pady=0)
        else:
            super().__init__(parent)
            self.pack(fill="both", expand=True, padx=0, pady=0)

        self.configure(background='black')

        # Trying to treat metapho.g_image_list like a global
        # doesn't work; need to make sure the g_image_list used is
        # the one from base metapho, not a new one created here.
        if img_list:
            imagelist.add_images([ tkPhoImage(f) for f in img_list ])

    def current_image(self):
        """Returns a tkPhoImage"""
        return imagelist.current_image()

    def add_image(self, imgpath):
        """Add an image to the image list.
        """
        imagelist.add_images(tkPhoImage(imgpath))

    def get_widget_size(self):
        return (self.winfo_width(),
                self.winfo_height())

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
        if tk_pho_image.VERBOSE:
            print("tkPhoWidget set_size", newsize)

        if not newsize and not self.widget_size:
            self.widget_size = self.get_widget_size()
            if tk_pho_image.VERBOSE:
                print("Actual widget size:", self.widget_size)

        # This can be called many times, so don't do anything
        # if nothing changed since last time.
        elif newsize == self.widget_size:
            if tk_pho_image.VERBOSE:
                print("Widget is already at size", self.widget_size)
            return

        if tk_pho_image.VERBOSE:
            print("Updating widget size to", newsize)
        self.widget_size = newsize

        self.show_image()

    def show_image(self):
        """Show the current image.
           Return 1 for success, 0 for valid image but not ready,
           -1 for invalid image or other error.
        """
        if type(imagelist.current_image()) is not tkPhoImage:
            if tk_pho_image.VERBOSE:
                print("Eek, no current image for show_image()")
            return

        if tk_pho_image.VERBOSE:
            print("tkPhoWidget.show_image, widget size is", self.widget_size,
                  "rotation", imagelist.current_image().rot)

        # fullsize mode should cancel any scaling.
        if self.fullsize:
            self.scale_factor = 1

        try:
            pil_img = self.resize_to_fit()
        except (FileNotFoundError, UnidentifiedImageError) as e:
            # Any exception means it's not a valid image and should
            # be removed from the list.
            if not imagelist.current_image().invalid:
                print("Eek, exception in show_image", file=sys.stderr)
                print("Exception was:", e)
            return
        if not pil_img:
            # This probably means that we are out of images.
            # But just in case that's not it:
            if not imagelist.image_list():
                raise IndexError("Imagelist is now empty")
            print("Eek, resize_to_fit didn't return an image!",
                  file=sys.stderr)
            return

        tkimg = ImageTk.PhotoImage(pil_img)
        if not self.fullscreen and not self.fixed_size:
            if tk_pho_image.VERBOSE:
                print("variable sized window: setting size to",
                      tkimg.width(), tkimg.height())
            self.set_size((tkimg.width(), tkimg.height()))
        self.config(image=tkimg)
        # self.image = tkimg
        self.photo = tkimg

        if tk_pho_image.VERBOSE:
            print("tk_pho_widget.show_image: display image %dx%d, widget %dx%d"
                  % (tkimg.width(), tkimg.height(),
                     self.winfo_reqwidth(), self.winfo_reqheight()))

        # At this point,
        # self.winfo_reqwidth(), self.winfo_reqheight()
        # should be the size of the new image,
        # though in practice it adds 2 pixels to both height and width.
        # self.winfo_width(), self.winfo_height()
        # is the size of the previous image, i.e. the current widget size,
        # except at the beginning where it's 1, 1

    def rescale(self, factor):
        self.scale_factor *= factor
        if imagelist.current_image():
            imagelist.current_image().display_img = None

    def resize_to_fit(self):
        """Resize the current image to fit in the current widget.
           but no larger than the bbox (width, height)
           (except in fullsize mode, where it translates as needed).
           Also rotate if needed.

           Return self.display_img, a PIL Image ready to display.
        """
        cur_img = imagelist.current_image()
        if not cur_img:
            if tk_pho_image.VERBOSE:
                print("resize_to_fit: no current image")
            return None

        # This will need the image size, so load the imageif it's not already
        if not cur_img.orig_img:
            cur_img.load()

        if tk_pho_image.VERBOSE:
            print("\nTkPhoWidget.resize_to_fit, imgno =",
                  imagelist.current_imageno(),
                  "\n  fullsize=", self.fullsize,
                  "\n  fullscreen=", self.fullscreen,
                  "\n  scale factor=", self.scale_factor,
                  "\n  rot=", cur_img.rot,
                  "\n  fullsize offset=", self.fullsize_offset,
                  "\n  widget size=", self.widget_size,
                  "\n  fixed size=", self.fixed_size)
            if cur_img.display_img:
                print("  display img is", cur_img.display_img.size)

        def adjust_rot(imgsize):
            if cur_img.rot % 180 != 0:
                return [ imgsize[1], imgsize[0] ]
            return imgsize

        def min_scaled_img_or_target(img, target):
            """If the image scaled by scale_factor is smaller than the
               window target size, don't scale it up any more than that.
               target is width, height.
            """
            scaled_img_size = adjust_rot([x * self.scale_factor
                                          for x in img.orig_img.size])
            if tk_pho_image.VERBOSE:
                print("scaled_img_size:", scaled_img_size, "for target", target)
            if (scaled_img_size[0] < target[0]
                and scaled_img_size[1] < target[1]):
                if tk_pho_image.VERBOSE:
                    print("Image smaller than target, using smaller window")
                return scaled_img_size
            return target

        if self.fullsize and self.fullscreen:
            if cur_img.display_img and (self.fullsize_offset[0]
                                        or self.fullsize_offset[1]):
                # there's an offset, so don't center.
                # The user has already dragged, so keep display_img.
                if tk_pho_image.VERBOSE:
                    print("Not centering: there's already an offset")
                return cur_img.display_img

            target_size = cur_img.orig_img.size
            if tk_pho_image.VERBOSE:
                print("fullsize and fullscreen: target size =", target_size)

            if cur_img.rot:
                if tk_pho_image.VERBOSE:
                    print("Rotating image to", cur_img.rot)
                    print("orig image is", cur_img.orig_img.size)
                cur_img.display_img = \
                    cur_img.orig_img.rotate(cur_img.rot, expand=True)
                cur_img.display_img = \
                    self.center_fullsize(cur_img.display_img)
                # Don't need target_size if not calling tkPhoWidget.resize_to_fit
                # if cur_img.rot % 180:
                #     target_size = target_size[::-1]
            else:
                cur_img.display_img = \
                    self.center_fullsize(cur_img.orig_img)
            if tk_pho_image.VERBOSE:
                print("cur_img.display_img has size", cur_img.display_img.size)

            # Don't call tkPhoWidget.resize_to_fit, which will mostly
            # duplicate what's already done here.
            return cur_img.display_img

        elif self.fullsize:
            target_size = adjust_rot(cur_img.orig_img.size)
            if tk_pho_image.VERBOSE:
                print("TkPhoWidget.resize_to_fit in fullsize mode", target_size)

        elif self.fullscreen:
            target_size = min_scaled_img_or_target(cur_img,
                                                   get_screen_size(self.root))
            if tk_pho_image.VERBOSE:
                print("TkPhoWidget.resize_to_fit, fullscreen, targeting",
                      target_size)

        elif not self.fixed_size:                  # normal variable-size window
            target_size = (self.root.winfo_screenwidth()
                           * FRAC_OF_SCREEN * self.scale_factor,
                           self.root.winfo_screenheight()
                           * FRAC_OF_SCREEN * self.scale_factor)
            target_size = min_scaled_img_or_target(cur_img, target_size)
            if tk_pho_image.VERBOSE:
                print("Resizable widget; target size =", target_size)

        else:                                      # fixed-size window
            img_size = [ x * self.scale_factor for x in cur_img.orig_img.size ]
            target_size = [ x * self.scale_factor for x in self.widget_size ]
            # Is the scaled image size smaller than the target size?
            # If so, don't scale up.
            # Nifty trick for comparing two arrays:
            if all(x < y for x, y in zip(img_size, target_size)):
                if tk_pho_image.VERBOSE:
                    print("Fixed-size window, scaled image smaller than window:"
                          " not scaling up")
                if cur_img.display_img:
                    return cur_img.display_img
                target_size = img_size
                # XXX This doesn't work for scaling up a small image to be
                # larger than the fixed-size window, but that's such a rare
                # edge case I'm not sure it matters.

            if tk_pho_image.VERBOSE:
                print("TkPhoWidget.resize_to_fit, fixed widget size:",
                      self.widget_size, "scaling to", target_size)

        return cur_img.resize_to_fit(target_size)

    def translate(self, dx, dy):
        """Calculate the offset of a fullsize image that has
           been dragged with the middle mouse.
           The actual translation will happen via the affine transform
           in center_fullsize.
        """
        self.fullsize_offset = (self.fullsize_offset[0] + dx,
                                self.fullsize_offset[1] + dy)
        if tk_pho_image.VERBOSE:
            print("tkPhoWidget.translate", dx, dy, "->",
                  self.fullsize_offset, end='')
        imagelist.current_image().display_img = None

    def center_fullsize(self, pil_img):
        """translate the given pil_img, assumed to be larger than the
           widget size, so that it's centered in the available space.
           Shift it by self.fullsize_offset, set from user mouse drags.
           This is only used when both fullscreen (display) and fullsize,
           before any user drags.

           Return the translated pil_img.
        """
        # Currently, this is only used in fullscreen mode,
        # so use the screen size.
        ww = self.root.winfo_screenwidth()
        wh = self.root.winfo_screenheight()

        # When in both fullscreen and fullsize, it's best to start
        # with the center of the image centered on the screen.
        # But also take into account fullsize_offset, which might
        # be set because the user dragged a fullscreen image.
        iw, ih = pil_img.size

        # If there's no offset and the image is smaller than the screen,
        # there's no need to transform anything.
        if iw < ww and ih < wh and \
           not self.fullsize_offset[0] and not self.fullsize_offset[1]:
            if tk_pho_image.VERBOSE:
                print("Small image, no need to translate")
            return pil_img

        # The dx and dy in the affine transformation move the image up and left
        # if they're positive.
        affine_dx = int((iw - ww)/2) - self.fullsize_offset[0]
        affine_dy = int((ih - wh)/2) - self.fullsize_offset[1]

        if tk_pho_image.VERBOSE:
            print("center_fullsize: affine transforming by\n    ",
                  '(', iw, '-', self.root.winfo_screenwidth(), ') / 2)',
                  '-', self.fullsize_offset[0],
                  '=', affine_dx,
                  ',\n    ',
                  '(', ih, '-', self.root.winfo_screenheight(), ') / 2)',
                  '-', self.fullsize_offset[1],
                  '=', affine_dy)
        return pil_img.transform((ww, wh), PILImage.AFFINE,
                                 # The 1, 1 on the diagonal are scale factors:
                                 # i.e. don't scale the image.
                                 (1, 0, affine_dx,
                                  0, 1, affine_dy))

        # then crop, https://stackoverflow.com/a/44684388
        # but that doesn't seem to be needed.
        # Is there any point to cropping off the extra lower right parts?
        # new_size = (g_image_list[g_cur_imgno].display_img.size[0] - dx,
        #             g_image_list[g_cur_imgno].display_img.size[1] - dy)
        # return cur_img.display_img.transform(
        #         new_size, PILImage.EXTENT, (0, 0, new_size[0], new_size[1]))

    def rotate(self, rotation):
        imagelist.current_image().rotate(rotation)

    def delete_current(self):
        """Remove the current image from the image list, and move the
           current_image pointer accordingly.
           Raises IndexError if there are no images left.
        """
        # Remove from the img_list
        deleted = imagelist.pop_image(advance=True)

        # delete the file on disk
        os.unlink(deleted.filename)

        self.show_image()

    def next_image(self):
        last_valid_image = imagelist.current_image()

        while True:
            try:
                imagelist.advance()
            except IndexError as e:
                # Can't go beyond last image. Re-raise the IndexError,
                # but only after setting the pointer back to the
                # last valid image.
                if tk_pho_image.VERBOSE:
                    print("Can't go beyond last image")
                imagelist.set_current_image(last_valid_image)
                if tk_pho_image.VERBOSE:
                    print("image list before re-raising IndexError:")
                    imagelist.print_imagelist()
                raise(e)

            # Is the current image valid?
            if imagelist.current_image().invalid:
                continue

            try:
                # Try to load it. This is also a test to make sure it's a
                # tkPhoImage: the base class MetaphoImage doesn't have load().
                imagelist.current_image().load()

            except (FileNotFoundError, UnidentifiedImageError,
                    IsADirectoryError, PermissionError) as e:
                print("Skipping", imagelist.current_image().relpath,
                      "because:", e)
                # PIL prints its errors with full paths, even if it was
                # a relative path passed in. I wish I could shorten them.
                imagelist.current_image().invalid = True
                imagelist.remove_image()
                continue
            except AttributeError as e:
                # Attribute error generally means
                #   MetaphoImage object has no attribute 'load'
                # meaning that we have a MetaphoImage in the image_list
                # instead of a tkPhoImage,
                # because the tagger read its tags from an existing Tags
                # file, but no GUI tkPhoImage was created for it because
                # it wasn't in the argument list.
                # In that case, skip it in the GUI, but don't delete it from
                # the image list because its tags still need to be preserved.
                # However, it can also happen when there are no viewable
                # images in the argument list.
                imagelist.current_image().invalid = True
                if tk_pho_image.VERBOSE:
                    print("AttributeError: Marked", imagelist.current_image(),
                          "as invalid")
                continue
            except Exception as e:
                print("Skipping an image for an unexpected reason:", type(e),
                      imagelist.current_image())
                imagelist.remove_image()
                continue

            # Whew, load() worked okay, the image is valid
            if tk_pho_image.VERBOSE:
                print("tkPhoWidget.next_image, to",
                      imagelist.current_imageno(),
                      "->", imagelist.current_image())

            self.fullsize_offset = 0, 0
            self.show_image()
            if tk_pho_image.VERBOSE:
                imagelist.print_imagelist()
            return

    def prev_image(self):
        if not imagelist.image_list():
            raise FileNotFoundError("No image list!")

        while True:
            try:
                imagelist.retreat()
            except IndexError:
                imagelist.set_current_imageno(-1)

            if imagelist.current_imageno() < 0:
                imagelist.set_current_imageno(0)
                if tk_pho_image.VERBOSE:
                    print("Can't look before first image")
                return

            # Is the current image valid?
            try:
                imagelist.current_image().load()
            except (FileNotFoundError, UnidentifiedImageError) as e:
                print("Skipping", imagelist.current_image(), e)
                imagelist.remove_image()
                continue
            except AttributeError:
                if tk_pho_image.VERBOSE:
                    print("AttributeError on", imagelist.current_image())

                    if type(imagelist.current_image()) is MetaphoImage:
                        # If it's a MetaphoImage, either it wasn't in the
                        # explicit argument list, or it can't
                        # be loaded by PIL (e.g. Tags)
                        imagelist.print_imagelist()
                continue

            # Whew, load() worked okay, the image is valid
            if tk_pho_image.VERBOSE:
                print("  to", imagelist.current_imageno(),
                      "->", imagelist.current_image())
            self.fullsize_offset = 0, 0
            self.show_image()
            return

    def goto_imageno(self, imagenum):
        num_images = imagelist.num_images()
        if imagenum >= num_images:
            imagelist.set_current_imageno(num_images)
            self.prev_image()
            return
        if imagenum < 0:
            # For negative numbers, count back, -1 being the last image
            imagelist.set_current_imageno(num_images + imagenum + 1)
            self.prev_image()
            return
        imagelist.set_current_imageno(imagenum - 1)
        self.fullsize_offset = 0, 0
        self.next_image()
        return

    def goto_image(self, image):
        for i, img in enumerate(imagelist.image_list()):
            if img == image:
                self.goto_imageno(i)
                return
        raise RuntimeError("tkPhoWidget: No such image " + str(image))


class SimpleImageViewerWindow:
    """A simple example of how to use tkPhoWidget.
       For something more elaborate, see tkpho.py.
    """
    def __init__(self, img_list=[], fixed_size=None):

        self.root = tk.Tk()

        self.root.title("Metapho Image Viewer")

        # To allow resizing, set self.fixed_size to None
        if fixed_size:
            self.fixed_size = fixed_size
        else:
            self.fixed_size = None
        self.viewer = tkPhoWidget(self.root, img_list,
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
        if tk_pho_image.VERBOSE:
            print("Bye")
        sys.exit(0)


if __name__ == '__main__':
    win = SimpleImageViewerWindow(sys.argv[1:], fixed_size=None)
    win.run()

