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

class ImageViewer(Gtk.DrawingArea):
    '''A generic PyGTK image viewer widget
    '''

    def __init__(self):
        super(ImageViewer, self).__init__()
        # self.connect("expose-event", self.expose_handler)
        self.connect("draw", self.draw)
        self.xgc_bg = None
        self.xgc_fg = None
        self.pixbuf = None
        self.label_text = None
        self.width = None
        self.height = None
        self.cur_img = None

        # The cairo thingamabob
        self.cr = None

    def draw(self, widget, cr):
        w, h = self.get_window().get_geometry()[2:4]
        if w != self.width or h != self.height:
            self.width = w
            self.height = h

        # Have we had load_image called, but we weren't ready for it?
        # Now, theoretically, we are ... so call it again.
        if w and h and self.cur_img and not self.pixbuf:
            self.prepare_image()

        self.cr = cr
        self.show_image()

    # Mapping from EXIF orientation tag to degrees rotated.
    # http://sylvana.net/jpegcrop/exif_orientation.html
    exif_rot_table = [ 0, 0, 180, 180, 270, 270, 90, 90 ]
    # Note that orientations 2, 4, 5 and 7 also involve a flip.
    # We're not implementing that right now, because nobody
    # uses it in practice.

    def load_image(self, img):
        # load_image is called from the MetaPhoWindow map event,
        # which happens before ImageViewer gets its own first draw event.
        # So we don't have a size yet when this is first called.
        if not self.width or not self.height:
            self.width, self.height = self.get_window().get_geometry()[2:4]

        self.cur_img = img
        if self.width and self.height:
            if self.cur_img:
                loaded = self.prepare_image()
            else:
                self.pixbuf = None
                self.clear()
                loaded = False

        self.label_text = None
        return loaded

    def prepare_image(self):
        '''Load the image passed in, and show it.
           img is a filename.
           Return True for success, False for error.
        '''
        self.label_text = None

        # Clean up memory from any existing pixbuf.
        # This still needs to be garbage collected before returning.
        if self.pixbuf:
            self.pixbuf = None

        try:
            newpb = GdkPixbuf.Pixbuf.new_from_file(self.cur_img.filename)

            # We can't do any of the rotation until the window appears
            # so we know our window size.
            # But we have to load the first pixbuf anyway, because
            # otherwise we may end up pointing to an image that can't
            # be loaded. Super annoying! We'll end up reloading the
            # pixbuf again after the window appears, so this will
            # slow down the initial window slightly.
            if not self.width:
                return True

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
            newpb = newpb.scale_simple(neww, newh,
                                       GdkPixbuf.InterpType.BILINEAR)

            # Rotate the image if needed
            if rot != 0:
                newpb = newpb.rotate_simple(rot)

            # newpb = newpb.apply_embedded_orientation()

            self.pixbuf = newpb

            loaded = True

        except Exception as e:
            print("Error reading image " + self.cur_img)
            print(e)
            self.pixbuf = None
            loaded = False

        # garbage collect the old pixbuf, if any, and the one we just read in.
        # GTK doesn't do its own garbage collection.
        newpb = None
        gc.collect()

        return loaded

    def show_image(self):
        if not self.pixbuf:
            print("pixbuf not ready yet")
            if not self.label_text:
                self.draw_text("No image")
            return

        # Center it:
        x = (self.width - self.pixbuf.get_width()) / 2
        y = (self.height - self.pixbuf.get_height()) / 2

        self.cr = self.get_window().cairo_create()
        Gdk.cairo_set_source_pixbuf(self.cr, self.pixbuf, x, y)
        self.cr.paint()

        if self.label_text:
            self.draw_text(self.label_text)


class ImageViewerWindow(Gtk.Window):
    '''Bring up a window that can view images.
    '''

    def __init__(self, file_list=None, width=1024, height=768):
        super(ImageViewerWindow, self).__init__()
        self.file_list = file_list
        self.imgno = 0

        # The size of the image viewing area:
        self.width = width
        self.height = height

        self.isearch = False

        self.set_border_width(10)

        self.connect("delete_event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)

        self.main_vbox = Gtk.VBox(spacing=8)

        self.viewer = ImageViewer()
        self.viewer.set_size_request(self.width, self.height)
        self.main_vbox.pack_start(self.viewer, True, True, 0)

        self.add(self.main_vbox)

        # Realize apparently happens too early.
        # self.connect("realize", self.expose_handler)

        if self.file_list:
            self.viewer.load_image(self.file_list[0])

    def run(self):
        self.show_all();
        self.set_opacity(.5)
        Gtk.main()

    def set_key_handler(self, fcn):
        self.connect("key-press-event", fcn, self)

    def new_image(self, imgfile):
        self.file_list = [ imgfile ]
        self.imgno = 0
        self.viewer.load_image(imgfile)
        if imgfile:
            self.viewer.show_image()

    def next_image(self):
        self.imgno = (self.imgno + 1) % len(self.file_list)
        self.viewer.load_image(self.file_list[self.imgno])
        self.viewer.show_image()

    def quit(self):
        Gtk.main_quit()

if __name__ == "__main__":

    def key_press_event(widget, event, imagewin):
        '''Handle a key press event anywhere in the window'''
        if event.string == " ":
            imagewin.next_image()
            return
        if event.string == "q":
            Gtk.main_quit()
            return

    import sys
    win = ImageViewerWindow(sys.argv[1:])
    win.set_key_handler(key_press_event)
    win.run()
