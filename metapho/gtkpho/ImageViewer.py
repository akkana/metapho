#!/usr/bin/env python

import metapho

import gtk
import gc
import glib, gobject

class ImageViewer(gtk.DrawingArea):
    '''A PyGTK image viewer widget for metapho.
    '''

    def __init__(self):
        super(ImageViewer, self).__init__()
        self.connect("expose-event", self.expose_handler)
        self.connect("configure_event", self.configure_event)
        self.gc = None
        self.pixbuf = None
        self.imgwidth = None
        self.imgheight = None
        self.cur_img = None
        self.truewidth = None
        self.trueheight = None

    def expose_handler(self, widget, event):
        # print "Expose"

        if not self.gc:
            self.gc = widget.window.new_gc()
            x, y, self.imgwidth, self.imgheight = self.get_allocation()

            # Have we had load_image called, but we weren't ready for it?
            # Now, theoretically, we are ... so call it again.
            if self.cur_img and not self.pixbuf:
                self.load_image(self.cur_img)

        self.show_image()

    def configure_event(self, widget, event):
        x, y, self.imgwidth, self.imgheight = self.get_allocation()
        # print "\nNew size: %d x %d" % (self.imgwidth, self.imgheight)

        # configure generates an expose so we don't need to call show_image().

    # Mapping from EXIF orientation tag to degrees rotated.
    # http://sylvana.net/jpegcrop/exif_orientation.html
    exif_rot_table = [ 0, 0, 180, 180, 270, 270, 90, 90 ]
    # Note that orientations 2, 4, 5 and 7 also involve a flip.
    # We're not implementing that right now, because nobody
    # uses it in practice.

    def load_image(self, img):
        '''Load the image passed in, and show it.
           img is a metapho.Image object.
           Return True for success, False for error.
        '''

        self.cur_img = img

        # Clean up memory from any existing pixbuf.
        # This still needs to be garbage collected before returning.
        if self.pixbuf:
            self.pixbuf = None

        try:
            self.pixbuf = gtk.gdk.pixbuf_new_from_file(img.filename)
            self.truewidth = self.pixbuf.get_width()
            self.trueheight = self.pixbuf.get_height()

            # self.scale_and_rotate(newpb)
            # This will set self.pixbuf if successful

            # self.show_image()
            loaded = True

        except glib.GError:
            self.pixbuf = None
            loaded = False

        # garbage collect the old pixbuf, if any, and the one we just read in:
        newpb = None
        gc.collect()

        return loaded

    def scale_and_rotate(self):
        '''A new pixbuf has just been read in, or else we have a new size
           that's smaller than the old size so we need to re-scale.
           Rotate and scale to the current size, putting the newly
           scaled pixbuf into self.pixbuf.
           For internal use: called from load_image.
           May call load_image to reload, if need be.
        '''
        # We can't do any of the rotation until the window appears
        # so we know our window size.
        # But we have to load the first pixbuf anyway, because
        # otherwise we may end up pointing to an image that can't
        # be loaded. Super annoying! We'll end up reloading the
        # pixbuf again after the window appears, so this will
        # slow down the initial window slightly.
        if not self.imgwidth:
            return True

        # Do we need to check rotation info for this image?
        if self.cur_img.rot == None:
            # Get the EXIF embedded rotation info.
            orient = self.pixbuf.get_option('orientation')
            if orient == None:    # No orientation specified; use 0
                orient = 0
            else:                 # convert to int array index
                orient = int(orient) - 1
            self.cur_img.rot = self.exif_rot_table[orient]

        # Scale the image to our display image size.
        # We need it to fit in the space available.
        # If we're not changing aspect ratios, that's easy.
        if self.cur_img.rot in [ 0, 180]:
            if self.truewidth > self.trueheight:   # horizontal format photo
                neww = self.imgwidth
                newh = self.trueheight * self.imgwidth / self.truewidth
            else:               # vertical format
                newh = self.imgheight
                neww = self.truewidth * self.imgheight / self.trueheight

            # Now we have the required new size. Is it different from
            # our current pixbuf's size, so we should reload from file?
            if neww != self.pixbuf.get_width() or \
               newh != self.pixbuf.get_height():
                self.load_image(self.cur_img)

        # If the image needs to be rotated 90 or 270 degrees,
        # scale so that the scaled width will fit in the image
        # height area -- even though it's still width because we
        # haven't rotated yet.
        else:     # We'll be changing aspect ratios
            if self.truewidth > self.trueheight:   # horizontal->vertical
                neww = self.imgheight
                newh = self.trueheight * self.imgheight / self.truewidth
            else:               # vertical format, -> horizontal
                neww = self.imgwidth
                newh = self.trueheight * self.imgwidth / self.truewidth

        # Finally, do the scale:
        if neww != self.pixbuf.get_width() or newh != self.pixbuf.get_height():
            self.pixbuf = self.pixbuf.scale_simple(neww, newh,
                                       gtk.gdk.INTERP_BILINEAR)

        # Rotate the image if needed
        if self.cur_img.rot != 0:
            self.pixbuf = self.pixbuf.rotate_simple(self.cur_img.rot)

        # self.pixbuf = self.pixbuf.apply_embedded_orientation()

    def show_image(self):
        '''Display the current image. If rotation or scaling is needed,
           may call load_image() and/or scale_and_rotate().
           This may be called from external classes, and is also called
           on expose and configure_notify events.
        '''
        if not self.gc:
            return

        if not self.pixbuf:
            return

        self.scale_and_rotate()

        # Clear the drawing area first
        self.window.draw_rectangle(self.gc, True, 0, 0,
                                   self.imgwidth, self.imgheight)

        x = (self.imgwidth - self.pixbuf.get_width()) / 2
        y = (self.imgheight - self.pixbuf.get_height()) / 2
        self.window.draw_pixbuf(self.gc, self.pixbuf, 0, 0, x, y)

    def rotate(self, rot):
        '''Change our idea of what our rotation should be,
           then reload (and re-rotate) if need be.
        '''
        if rot == self.cur_img.rot:
            return

        self.cur_img.rot = (self.cur_img.rot + rot + 360) % 360

        # XXX we don't always need to reload: could make this more efficient.
        self.load_image(self.cur_img)

class ImageViewerWindow(gtk.Window):
    '''Standalone window with an ImageViewer inside it.
       This can be used as a simple image viewer from the command line,
       or as a separate window in another app, e.g. the metapho zoom window.
    '''
    def __init__(self, *args, **kwargs):
        '''Positional args are a list of image filenames.
           Keyword args:
               quit: function to call when the user presses 'q'.
                     To use as a standalone app, pass quit=gtk.main_quit.
                     By default, q will merely hide() the window.
        '''
        super(ImageViewerWindow, self).__init__()

        self.imglist = list(args)

        if 'quit' in kwargs:
            self.quitfcn = kwargs['quit']
        else:
            self.quitfcn = self.hide

        self.cur_img_index = 0
        self.cur_img = self.imglist[0]

        # Expanded to full image size, or scaled to the display size?
        self.expanded = False

        # We can get screenwidth with gtk.gdk.screen_width() (and height),
        # but GTK sizes are messed up: if we initially self.resize()
        # to the screen size, then the drawing area will automatically
        # adjust to be a little smaller, to allow for the window chrome.
        # But that only happens on the first resize; subsequently,
        # if we self.resize() to the screen width and height,
        # the contained drawing area will try to be that size
        # and we'll end up with some of the window off screen.
        # This is all insane, so instead, let's just keep the window
        # a little smaller than the actual screen
        self.screen_width = gtk.gdk.screen_width() - 20
        self.screen_height = gtk.gdk.screen_height() - 50

        self.connect("delete_event", gtk.main_quit)
        self.connect("destroy", gtk.main_quit)
        self.connect("key-press-event", self.key_press_event)

        self.imgviewer = ImageViewer()
        self.add(self.imgviewer)

        # Set a ridiculously small size at first:
        # without this, we'll never be able to resize
        # below the initial size (undocumented PyGTK trick).
        self.imgviewer.set_size_request(10, 10)

        self.load_image()
        self.fit_on_screen()
        self.show_image()

        self.imgviewer.show()
        self.show()

    def add_image(self, filename):
        '''Add an image to the list, and show it.
           Don't remove the other images, though; let the user
           use 'p' to get back to them if desired.
        '''
        self.imglist.append(filename)
        self.cur_img_index = len(self.imglist) - 1
        self.cur_img = self.imglist[self.cur_img_index]
        self.fit_on_screen()
        self.show_image()

    def load_image(self):
        '''Load (or reload) self.cur_img from file.
        '''
        loaded = False
        while True:
            img = metapho.Image(self.cur_img)
            loaded = self.imgviewer.load_image(img)
            if loaded:
                return

            # It didn't load properly as an image.
            print self.cur_img, "is not an image."
            self.imglist.remove(self.cur_img)
            if self.cur_img_index >= len(self.imglist):
                self.cur_img_index = len(self.imglist) - 1
            self.cur_img = self.imglist[self.cur_img_index]

    def show_image(self):
        self.imgviewer.show_image()

    def fit_on_screen(self):
        w = self.imgviewer.truewidth
        h = self.imgviewer.trueheight
        if w <= self.screen_width and h <= self.screen_height:
            self.resize(w, h)
        else:
            self.resize(self.screen_width, self.screen_height)

        self.expanded = False

    def expand_to_full_size(self):
        self.resize(self.imgviewer.truewidth, self.imgviewer.trueheight)
        self.expanded = True

    def key_press_event(self, widget, event):
        # q quits.
        if event.keyval == gtk.keysyms.q:
            self.quitfcn()
            return True

        # f toggles between fullscreen and full-zoom:
        if event.keyval == gtk.keysyms.f:
            if self.expanded:
                self.fit_on_screen()
            else:
                self.expand_to_full_size()
            return True

        # Space moves to the next image:
        if event.keyval == gtk.keysyms.space:
            if self.cur_img_index < len(self.imglist) - 1:
                self.cur_img_index += 1
                self.cur_img = self.imglist[self.cur_img_index]
                self.load_image()
                self.show_image()
            return True

        # Backspace moves to the previous image:
        if event.keyval == gtk.keysyms.BackSpace:
            if self.cur_img_index > 0:
                self.cur_img_index -= 1
                self.cur_img = self.imglist[self.cur_img_index]
                self.load_image()
                self.show_image()
            return True

        return False

if __name__ == '__main__':
    import sys

    if len(sys.argv) <= 1:
        print "Usage: %s img [img img ...]" % sys.argv[0]
        sys.exit(1)
    ivw = ImageViewerWindow(*sys.argv[1:], quit=gtk.main_quit)

    gtk.main()
