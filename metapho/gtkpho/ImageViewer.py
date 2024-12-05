#!/usr/bin/env python

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Pango

# import glib
import cairo
import gc

from metapho import Image

DEBUG = False


class ImageViewer(Gtk.DrawingArea):
    """A simple PyGTK image viewer widget.
    """

    def __init__(self):
        super().__init__()

        self.cr = None

        self.connect("draw", self.draw)
        self.connect("size-allocate", self.detect_resize)

        self.pixbuf = None
        self.label_text = None

        self.width = 0
        self.height = 0

        self.savewidth = None
        self.saveheight = None

        # Zoomed to full resolution?
        self.fullzoom = False
        # Function to call when we want to resize the window
        self.resize_fn = None

        # Current image is a Image.
        self.cur_img = None


    def get_window_size(self):
        """Return width, height of the current window allocation."""
        # Before the window is created, get_allocation will return 1, 1
        # which plays havoc with other calculations.
        # print("get_window_size traceback:")
        # traceback.print_stack()
        try:
            rect = self.get_allocation()
            if DEBUG:
                print("get_window_size returning %dx%d"
                      % (rect.width, rect.height))
            # Early on, GTK gives us a bogus 1x1 window size,
            # which messes things up.
            if rect.width < 10 or rect.height < 10:
                return 0, 0
            return rect.width, rect.height
        except:
            return 0, 0


    def detect_resize(self, w, rect):
        self.width, self.height = self.get_window_size()
        if DEBUG:
            print("detect_resize to %dx%d" % (self.width, self.height))
        self.prepare_image()
        self.show_image()


    def draw(self, widget, cr):
        """Draw the image, scaled appropriately."""
        self.cr = cr
        # w, h = self.get_window_size()
        # if w != self.width or h != self.height:
        #     if DEBUG:
        #         print("draw: window size changed to %dx%d" % (w, h))
        #     self.width = w
        #     self.height = h
        # Calling self.get_window_size() here somehow leads to an
        # infinite loop. So I guess it's better to rely on detect_resize.
        w = self.width
        h = self.height

        # Have we had load_image called, but we weren't ready for it?
        # Now, theoretically, we are ... so call it again.
        if w and h and self.cur_img and not self.pixbuf:
            self.prepare_image()

        self.show_image(cr)

    # Mapping from EXIF orientation tag to degrees rotated.
    # http://sylvana.net/jpegcrop/exif_orientation.html
    exif_rot_table = [ 0, 0, 180, 180, 270, 270, 90, 90 ]
    # Note that orientations 2, 4, 5 and 7 also involve a flip.
    # We're not implementing that right now, because nobody
    # uses it in practice.

    def load_image(self, img):
        """Load an image from a filename or metaphe.Image.
           Return 1 for success, 0 for valid image but not ready,
           -1 for invalid image or other error.
        """
        # load_image is called from the MetaPhoWindow map event,
        # which happens before ImageViewer gets its own first draw event.
        # So we don't have a size yet when this is first called.
        if not self.width or not self.height:
            if DEBUG:
                print("load_image with no window size")
                return

        if isinstance(img, Image):
            self.cur_img = img
        else:
            self.cur_img = Image(img)

        self.label_text = None

        if not self.window or not self.width or not self.height:
            if DEBUG:
                print("Oops, window", self.window, "width", self.width,
                      "height", self.height)
            return 0

        if self.cur_img:
            loaded = self.prepare_image()
        else:
            self.pixbuf = None
            self.clear()
            loaded = -1

        return loaded


    def prepare_image(self):
        """Load the current image, scale and rotate, and show it.
           img is a filename.
           Return 1 for success, 0 for valid image but not ready,
           -1 for invalid image or other error.
        """

        # We can't do any of the rotation until the window appears
        # so we know our window size.
        # But we have to load the first pixbuf anyway, because
        # otherwise we may end up pointing to an image that can't
        # be loaded. Super annoying! We'll end up reloading the
        # pixbuf again after the window appears, so this will
        # slow down the initial window slightly.
        if DEBUG:
            print("in prepare_image, size is %dx%d" % (self.width, self.height))
        if not self.width or not self.height:
            if DEBUG:
                print("prepare_image called with no window size")
            return -1

        if not self.cur_img:
            if DEBUG:
                print("No current image")
            return -1

        self.label_text = None

        # Clean up memory from any existing pixbuf.
        # This still needs to be garbage collected before returning.
        if self.pixbuf:
            self.pixbuf = None

        try:
            newpb = GdkPixbuf.Pixbuf.new_from_file(self.cur_img.filename)
            if DEBUG:
                print("Got a new pixbuf from", self.cur_img.filename)

            # Do we need to check rotation info for this image?
            # Get the EXIF embedded rotation info.
            orient = newpb.get_option('orientation')
            if orient is None :    # No orientation specified; use 0
                orient = 0
            else :                 # convert to int array index
                orient = int(orient) - 1
            rot = self.exif_rot_table[orient]

            # Scale the image to our display image size.
            # We need it to fit in the space available.
            # If we're not changing aspect ratios, that's easy.
            if self.fullzoom:
                self.width = newpb.get_width()
                self.height = newpb.get_height()
                if self.resize_fn:
                    self.resize_fn(self.width, self.height)

            else:
                oldw = newpb.get_width()
                oldh = newpb.get_height()
                if rot in [ 0, 180]:
                    if oldw > oldh :     # horizontal format photo
                        neww = self.width
                        newh = oldh * self.width / oldw
                    else :               # vertical format
                        newh = self.height
                        neww = oldw * self.height / oldh

                # If the image needs to be rotated 90 or 270 degrees,
                # scale so that the scaled width will fit in the image
                # height area -- even though it's still width because we
                # haven't rotated yet.
                else :     # We'll be changing aspect ratios
                    if oldw > oldh :     # horizontal format, will be vertical
                        neww = self.height
                        newh = oldh * self.height / oldw
                    else :               # vertical format, will be horiz
                        neww = self.width
                        newh = oldh * self.width / oldw

                # Finally, do the scale:
                if DEBUG:
                    print("window size: %dx%d" % (self.width, self.height))
                    print("image size: %dx%d" % (oldw, oldh))
                    print("pixbuf size: %dx%d" % (oldw, oldh))
                    print("scaling to: %dx%d" % (neww, newh))
                newpb = newpb.scale_simple(neww, newh,
                                           GdkPixbuf.InterpType.BILINEAR)

            # Rotate the image if needed
            if rot != 0:
                newpb = newpb.rotate_simple(rot)

            # newpb = newpb.apply_embedded_orientation()

            self.pixbuf = newpb

            loaded = True

        except gi.repository.GLib.Error as e:
            if DEBUG:
                print("Error reading image " + self.cur_img.filename)
                print(e)
            print("Skipping %s: not an image" % self.cur_img.filename)
            self.pixbuf = None
            loaded = False

        # garbage collect the old pixbuf, if any, and the one we just read in.
        # GTK doesn't do its own garbage collection.
        newpb = None
        gc.collect()

        if loaded:
            self.show_image()
            return 1
        else:
            return 0


    def show_image(self, cr=None):
        if not self.window:
            if DEBUG:
                print("No window yet, can't show image")
            return
        if not self.pixbuf:
            if DEBUG:
                print("No pixbuf, can't show image")
            return

        if not cr:
            cr = self.cr
        if not cr:
            if DEBUG:
                print("eek, can't show image without cairo context")
            return
        self.clear(cr)

        # Center the image:
        x = (self.width - self.pixbuf.get_width()) / 2
        y = (self.height - self.pixbuf.get_height()) / 2

        self.clear(cr)
        Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, x, y)
        cr.paint()

        # But cairo doesn't actually draw anything unless
        # you force it to:
        self.queue_draw()


    def clear(self, cr):
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, self.width, self.height)
        cr.fill()


    def toggle_fullsize(self):
        """Toggle whether images are shown at full size,
           in a window that may not fit on the screen,
           or scaled to the existing window size.
           Note that ImageViewer can't directly change the size
           of its containing window; if you want the viewer to
           be able to do that, set the viewer's resize_fn,
           as ImageViewerWindow does.
        """
        if not self.cur_img:
            return

        if self.fullzoom:
            self.width = self.savewidth
            self.height = self.saveheight
            self.fullzoom = False

            if self.resize_fn:
                self.resize_fn(self.width, self.height)

        else:
            self.savewidth = self.width
            self.saveheight = self.height
            self.fullzoom = True

        self.prepare_image()
        self.show_image()


class ImageViewerWindow(Gtk.Window):
    """Bring up a window that can view images.
       Pass in a list of Images, or a list of filenames,
       or just one Image or filename.
    """

    def __init__(self, img_list=None, width=1024, height=768, exit_on_q=True):
        super(ImageViewerWindow, self).__init__()

        if type(img_list) is str:
            self.img_list = [ Image(img_list) ]
        elif isinstance(img_list, Image):
            self.img_list = [ img_list ]
        elif hasattr(img_list, "__getitem__"):
            self.img_list = [ f if isinstance(f, Image) else Image(f)
                              for f in img_list ]
        else:
            self.img_list = None

        self.exit_on_q = exit_on_q

        self.imgno = 0

        # The size of the image viewing area:
        self.width = width
        self.height = height

        self.isearch = False

        self.set_border_width(10)

        # Clicking the windowmanager x will send a delete event
        self.connect("delete_event", self.delete)

        # We don't seem to need the destroy event
        # self.connect("destroy", self.destroy)

        self.connect("key-press-event", self.key_press_event, self)

        self.main_vbox = Gtk.VBox(spacing=8)

        self.viewer = ImageViewer()
        self.viewer.window = self
        self.viewer.set_size_request(self.width, self.height)
        self.viewer.resize_fn =  self.resize_fn
        self.main_vbox.pack_start(self.viewer, True, True, 0)

        self.add(self.main_vbox)

        # Realize apparently happens too early.
        # self.connect("realize", self.expose_handler)

        while self.img_list:
            loaded = self.viewer.load_image(self.img_list[0])
            if loaded >= 0:
                break
            # Couldn't load that image. Remove it from the list.
            self.img_list = self.img_list[1:]

    def run(self):
        self.show_all()
        Gtk.main()

    def add_image(self, img):
        if not isinstance(img, Image):
            img = Image(img)

        try:
            self.imgno = self.img_list.index(img)
        except (AttributeError, ValueError):
            self.img_list.append(img)
            self.imgno = len(self.img_list) - 1

        self.viewer.load_image(img)
        self.viewer.show_image()

    def next_image(self):
        if not self.img_list:
            if DEBUG:
                print("No img_list")
            return
        if DEBUG:
            print("Going from", self.imgno, "->", self.img_list[self.imgno])
        while True:
            self.imgno += 1
            if self.imgno >= len(self.img_list):
                self.imgno = len(self.img_list) - 1
                if DEBUG:
                    print("Can't go beyond last image")
                return
            if DEBUG:
                print("  to", self.imgno, "->", self.img_list[self.imgno])
            loaded = self.viewer.load_image(self.img_list[self.imgno])
            if loaded == 1:
                self.viewer.show_image()
                return

    def prev_image(self):
        if not self.img_list:
            return
        while True:
            self.imgno -= 1
            if self.imgno < 0:
                self.imgno = 0
                if DEBUG:
                    print("Can't go before first image")
                return
            loaded = self.viewer.load_image(self.img_list[self.imgno])
            if loaded == 1:
                self.viewer.show_image()
                return

    def quit(self):
        Gtk.main_quit()

    def delete(self, parentwin, event):
        if self.exit_on_q:
            Gtk.main_quit()
        else:
            self.hide()
        return True

    def resize_fn(self, width, height):
        """A function the ImageViewer can call when it's in fullsize
           mode and wants to resize the window.
        """
        self.resize(self.viewer.width, self.viewer.height)
        # self.set_default_size(self.viewer.width, self.viewer.height)
        # self.resize(self.viewer.width, self.viewer.height)

    def key_press_event(self, widget, event, imagewin):
        """Handle a key press event anywhere in the window.
           Optional; to install it, call handle_key_presses.
        """
        if event.string == " ":
            self.next_image()
            return
        if event.keyval == Gdk.KEY_BackSpace:
            self.prev_image()
            return
        if event.string == "f":
            self.viewer.toggle_fullsize()
            return
        if event.string == "q":
            if self.exit_on_q:
                Gtk.main_quit()
            else:
                self.hide()
            return


def main():
    import sys
    win = ImageViewerWindow(sys.argv[1:], exit_on_q=True)
    try:
        win.run()
    except KeyboardInterrupt:
        if DEBUG:
            print("Ctrl-C")
        win.quit()


if __name__ == "__main__":
    main()
