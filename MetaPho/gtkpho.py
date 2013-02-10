#!/usr/bin/env python

# GTK UI classes for MetaPho: an image tagger and viewer.

# Copyright 2013 by Akkana Peck: share and enjoy under the GPL v2 or later.

from . import MetaPho

import gtk
import gc
import glib
import os

class TagViewer(MetaPho.Tagger, gtk.Table) :
    '''A PyGTK widget for showing tags.
    '''
    def __init__(self) :
        MetaPho.Tagger.__init__(self)
        gtk.Table.__init__(self, 2, 20, False)

        self.title = gtk.Label("Tags")
        self.attach_defaults(self.title, 0, 2, 0, 1 );
        self.title.show()
        self.cur_img = None
        self.highlightBG = gtk.gdk.color_parse("#FFFFFF")
        self.greyBG = gtk.gdk.color_parse("#DDDDDD")
        self.ignore_events = False

        # Set up a bunch of entries, also setting the table size:
        self.buttons = []
        self.entries = []
        for i in range(0, 20) :
            button = gtk.ToggleButton(str(i))
            self.attach_defaults(button, 0, 1, i+1, i+2 );
            self.buttons.append(button)
            button.connect("toggled", self.toggled, i)

            entry = gtk.Entry()
            entry.set_width_chars(35)
            #entry.connect("changed", self.entry_changed, i)
            #entry.connect("focus-in-event", self.focus_in, i)
            entry.connect("focus-out-event", self.focus_out, i)
            self.attach_defaults(entry, 1, 2, i+1, i+2 );
            self.entries.append(entry)

        self.show()

    def change_tag(self, tagno, newstr) :
        if tagno < len(self.tagList) :
            self.tagList[tagno] = newstr
        else :
            newtag = self.addTag(newstr, self.cur_img)
            self.highlightTag(newtag, True)

    def focus_out(self, entry, event, tagno) :
        entry_text = entry.get_text()
        # Ignore blank entries
        if entry_text.strip() == '' :
            return
        self.change_tag(tagno, entry_text)
        return True

    def toggled(self, button, tagno) :
        # We'll get a recursion loop if we don't block events here --
        # adding and removing tags update the GUI state, which
        # changes the toggle button state, which calls toggled() again.
        if self.ignore_events :
            return

        # get_active() is the state *after* the button has been pressed.
        if button.get_active() :
            # Was off, now on, so add the tag.
            self.addTag(tagno, self.cur_img)
        else :
            # It's already on, so toggle it off.
            self.removeTag(tagno, self.cur_img)
        return True

    def check_entry_tag(focused_widget) :
        '''At certain times, such as just before exit, the main window
           may call us to alert us that a tag may have changed.
           We need to find out which entry contains it and check the tag.
        '''
        for i, ent in enumerate(self.entries) :
            if focused_widget == ent :
                self.focus_out(ent, None, i)

    def displayTags(self) :
        '''Call this after readTags() has been read for all directories.'''

        for i in range(len(self.entries)) :
            if i < len(self.tagList) :
                # print "Tag", i, ":", self.tagList[i]
                self.entries[i].set_text(self.tagList[i])

        if len(self.tagList) > len(self.entries) :
            print "Too many tags -- can't show all", \
                len(self.tagList)

    def highlightTag(self, tagno, val) :
        '''Turn tag number tagno on (if val=True) or off (val=False).'''
        if self.buttons[tagno].get_active() != val :
            self.ignore_events = True
            self.buttons[tagno].set_active(val)
            self.ignore_events = False

        if val :
            self.entries[tagno].modify_base(gtk.STATE_NORMAL, self.highlightBG)
        else :
            self.entries[tagno].modify_base(gtk.STATE_NORMAL, self.greyBG)

    def setImage(self, img) :
        self.cur_img = img

        self.title.set_text(os.path.basename(img.filename))

        # Clear all currently highlighted tags
        for i in xrange(len(self.entries)) :
            self.highlightTag(i, False)

        # Highlight just the ones associated with this image
        for i, tagstr in enumerate(img.tags) :
            self.highlightTag(img.tags[i], True)

        return

    def addTag(self, tag, img) :
        '''Add a tag to the given image.
           img is a MetaPho.Image.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index (in the global tags list) of the tag just added,
           or None if error.
        '''
        # Call the base class to make sure the tag is there:
        tagindex = MetaPho.Tagger.addTag(self, tag, img)

        # Now display it, if possible
        if tagindex < len(self.entries) :
            self.highlightTag(tagindex, True)

        return tagindex

    def removeTag(self, tag, img) :
        if not type(tag) is int :
            tagstr = tag
            tag = self.tagList.index(tagstr)
            if tagstr < 0 :
                print "No such tag", tagstr
                return

        MetaPho.Tagger.removeTag(self, tag, img)

        self.highlightTag(tag, False)

    def toggleTag(self, tagno, img) :
        '''Toggle tag number tagno for the given img.'''
        MetaPho.Tagger.toggleTag(self, tagno, img)
        if tagno < len(self.entries) :
            self.highlightTag(tagno, not self.buttons[tagno].get_active())

    def focus_next_entry(self, win) :
        '''Set focus to the next available entry.
           If we're already typing in a new tag entry that hasn't been
           saved yet, save it first before switching to the new one.
        '''
        newindex = len(self.tagList)
        curtext = self.entries[newindex].get_text()

        if curtext.strip() != '' :
            # user just typed something, so save it as if we got a focus out
            self.change_tag(newindex, curtext)
            newindex += 1

        win.set_focus(self.entries[newindex])
        self.highlightTag(newindex, True)

class ImageViewer(gtk.DrawingArea) :
    '''A PyGTK image viewer widget for MetaPho.
    '''

    def __init__(self) :
        super(ImageViewer, self).__init__()
        self.connect("expose-event", self.expose_handler)
        self.gc = None
        self.pixbuf = None
        self.imgwidth = None
        self.imgheight = None
        self.cur_img = None

    def expose_handler(self, widget, event) :
        #print "Expose"

        if not self.gc :
            self.gc = widget.window.new_gc()
            x, y, self.imgwidth, self.imgheight = self.get_allocation()

            # Have we had loadImage called, but we weren't ready for it?
            # Now, theoretically, we are ... so call it again.
            if self.cur_img and not self.pixbuf :
                self.loadImage(self.cur_img)

        self.showImage()

    # Mapping from EXIF orientation tag to degrees rotated.
    # http://sylvana.net/jpegcrop/exif_orientation.html
    exif_rot_table = [ 0, 0, 180, 180, 270, 270, 90, 90 ]
    # Note that orientations 2, 4, 5 and 7 also involve a flip.
    # We're not implementing that right now, because nobody
    # uses it in practice.

    def loadImage(self, img) :
        '''Load the image passed in, and show it.
           img is a MetaPho.Image object.
           Return True for success, False for error.
        '''

        self.cur_img = img

        # Clean up memory from any existing pixbuf.
        # This still needs to be garbage collected before returning.
        if self.pixbuf :
            self.pixbuf = None

        try :
            newpb = gtk.gdk.pixbuf_new_from_file(img.filename)

            # We can't do any of the rotation until the window appears
            # so we know our window size.
            # But we have to load the first pixbuf anyway, because
            # otherwise we may end up pointing to an image that can't
            # be loaded. Super annoying! We'll end up reloading the
            # pixbuf again after the window appears, so this will
            # slow down the initial window slightly.
            if not self.imgwidth :
                return True

            # Do we need to check rotation info for this image?
            if img.rot == None :
                # Get the EXIF embedded rotation info.
                orient = newpb.get_option('orientation')
                if orient == None :    # No orientation specified; use 0
                    orient = 0
                else :                 # convert to int array index
                    orient = int(orient) - 1
                img.rot = self.exif_rot_table[orient]

            # Scale the image to our display image size.
            # We need it to fit in the space available.
            # If we're not changing aspect ratios, that's easy.
            oldw = newpb.get_width()
            oldh = newpb.get_height()
            if img.rot in [ 0, 180] :
                if oldw > oldh :     # horizontal format photo
                    neww = self.imgwidth
                    newh = oldh * self.imgwidth / oldw
                else :               # vertical format
                    newh = self.imgheight
                    neww = oldw * self.imgheight / oldh

            # If the image needs to be rotated 90 or 270 degrees,
            # scale so that the scaled width will fit in the image
            # height area -- even though it's still width because we
            # haven't rotated yet.
            else :     # We'll be changing aspect ratios
                if oldw > oldh :     # horizontal format, will be vertical
                    neww = self.imgheight
                    newh = oldh * self.imgheight / oldw
                else :               # vertical format, will be horiz
                    neww = self.imgwidth
                    newh = oldh * self.imgwidth / oldw

            # Finally, do the scale:
            newpb = newpb.scale_simple(neww, newh,
                                             gtk.gdk.INTERP_BILINEAR)

            # Rotate the image if needed
            if img.rot != 0 :
                newpb = newpb.rotate_simple(img.rot)

            # newpb = newpb.apply_embedded_orientation()

            self.pixbuf = newpb

            self.showImage()
            loaded = True

        except glib.GError :
            self.pixbuf = None
            loaded = False

        # garbage collect the old pixbuf, if any, and the one we just read in:
        newpb = None
        gc.collect()

        return loaded

    def showImage(self) :
        if not self.gc :
            return

        if not self.pixbuf :
            return

        # Clear the drawing area first
        self.window.draw_rectangle(self.gc, True, 0, 0,
                                   self.imgwidth, self.imgheight)

        x = (self.imgwidth - self.pixbuf.get_width()) / 2
        y = (self.imgheight - self.pixbuf.get_height()) / 2
        self.window.draw_pixbuf(self.gc, self.pixbuf, 0, 0, x, y)

    def rotate(self, rot) :
        self.cur_img.rot = (self.cur_img.rot + rot + 360) % 360

        # XXX we don't always need to reload: could make this more efficient.
        self.loadImage(self.cur_img)

