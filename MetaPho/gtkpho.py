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
    def __init__(self, parentwin) :
        MetaPho.Tagger.__init__(self)
        self.num_rows = 26
        gtk.Table.__init__(self, 4, self.num_rows, False)

        self.parentwin = parentwin

        self.title = gtk.Label("Tags")
        self.attach(self.title, 0, 4, 0, 1 );

        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("Tag category:"), expand=False)

        # Set up a combobox with a text entry, so the user can change cats.
        self.categorysel = gtk.combo_box_entry_new_text()

        hbox.pack_start(self.categorysel, expand=True)
        self.attach(hbox, 0, 4, 1, 2 );

        self.cur_img = None
        self.highlight_bg = gtk.gdk.color_parse("#FFFFFF")
        self.greyBG = gtk.gdk.color_parse("#DDDDDD")
        self.matchBG = gtk.gdk.color_parse("#DDFFEE")
        self.ignore_events = False

        # Set up a bunch of entries, also setting the table size:
        self.buttons = []
        self.entries = []
        self.button_names = []
        for j in range(0, 2) :
            for i in range(0, self.num_rows) :
                if j <= 0 :
                    buttonchar = chr(i + ord('a'))
                    left = 0
                else :
                    buttonchar = chr(i + ord('A'))
                    left = 2

                button = gtk.ToggleButton(buttonchar)
                self.attach(button, left, left+1, i+2, i+3 );
                self.buttons.append(button)
                button.connect("toggled", self.toggled, len(self.entries))

                entry = gtk.Entry()
                entry.set_width_chars(25)
                #entry.connect("changed", self.entry_changed, i)
                #entry.connect("focus-in-event", self.focus_in, i)
                entry.connect("focus-out-event", self.focus_out,
                              len(self.entries))
                self.attach(entry, left+1, left+2, i+2, i+3 );
                self.entries.append(entry)

        self.show()

    def change_tag(self, tagno, newstr) :
        if tagno < len(self.tag_list) :
            self.tag_list[tagno] = newstr
        else :
            newtag = self.add_tag(newstr, self.cur_img)
            self.highlight_tag(newtag, True)

    def clear_tags(self, img) :
        MetaPho.Tagger.clear_tags(self, img)

        # also update the UI
        for i in xrange(len((self.entries))) :
            self.highlight_tag(i, False)

        # leave nothing focused
        self.focus_none()

    def unhighlight_empty_entries(self) :
        '''Check whether any entries are empty.
           If so, make sure they're unhighlighted.
        '''
        for i, ent in enumerate(self.entries) :
            if self.buttons[i].get_active() and not ent.get_text() :
                self.highlight_tag(i, False)

    def focus_none(self) :
        '''Un-focus any currently focused text entry,
           leaving nothing focused.
           If there was a focused entry and it was empty,
           de-select the corresponding toggle button.
        '''
        focused = self.parentwin.get_focus()

        # if focus was in a text entry, un-highlight that entry.
        # if (type(focused) is gtk.Entry) :
        #     print "It's an entry"
        #     entryno = self.entries.index(focused)
        #     self.highlight_tag(entryno, False)

        # Make sure we're leaving nothing focused:
        self.unhighlight_empty_entries()
        self.parentwin.set_focus(None)

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
            self.add_tag(tagno, self.cur_img)
        else :
            # It's already on, so toggle it off.
            self.remove_tag(tagno, self.cur_img)

        # Often when the user clicks on a button it's because
        # focus was in a text field. We definitely don't want it
        # to stay there.
        self.focus_none()

        return True

    def check_entry_tag(focused_widget) :
        '''At certain times, such as just before exit, the main window
           may call us to alert us that a tag may have changed.
           We need to find out which entry contains it and check the tag.
        '''
        for i, ent in enumerate(self.entries) :
            if focused_widget == ent :
                self.focus_out(ent, None, i)

    def display_tags(self) :
        '''Called after read_tags() has been read for all directories.'''

        # Add our categories to the combo.
        for catname in self.categories.keys():
            self.categorysel.append_text(catname)

        # And add an extra category that the user can change to something else:
        self.categorysel.append_text("** add new category **")

        # Set the first category as current, and display its tags.
        self.current_category = self.categories.keys()[0]
        self.display_tags_for_category(self.current_category)

        self.categorysel.set_active(0)
        self.categorysel.connect("changed", self.change_category)

    def display_tags_for_category(self, catname) :
        # Is this a new category, not in the list, e.g. "** add new **" ?
        if catname not in self.categories.keys() :
            for i in range(len(self.entries)) :
                self.entries[i].set_text("")
                self.highlight_tag(i, False)
            return

        if self.cur_img :
            cur_img_tags = [ self.tag_list[i] for i in self.cur_img.tags ]
        else :
            cur_img_tags = []
        self.current_category = catname
        for i in range(len(self.entries)) :
            if i < len(self.categories[catname]) :
                curtag = self.tag_list[self.categories[catname][i]]
                self.entries[i].set_text(curtag)
                self.highlight_tag(i, curtag in cur_img_tags)

            else :
                self.entries[i].set_text("")
                self.highlight_tag(i, False)

        if len(self.categories[catname]) > len(self.entries) :
            print "Too many tags in category %s -- can't show all %d" % \
                (catname, len(self.categories[catname]))

    def change_category(self, combobox) :
        '''The callback when the combobox is changed by the user.
        '''
        self.update_edited_category()

        # The pygtk docs say this only tracks combobox changes,
        # not changes to the underlying text entry, but it lies:
        # typing in the entry unfortunately calls this function too.
        # Unfortunately, ComboBoxEntry has no way of distinguishing
        # changes due to choosing a different entry versus editing
        # the current one. So we have to keep track of which one
        # was active, and see if it changed.
        keys = self.categories.keys()
        try :
            oldcatno = self.categories.keys().index(self.current_category)
        except ValueError :
            oldcatno = -1
        if combobox.get_active() == oldcatno or combobox.get_active() < 0 :
            # We haven't changed categories, just edited the current one.
            # self.current_category = combobox.get_active_text()
            return self.update_edited_category

        if combobox.get_active() < len(keys) :
            self.display_tags_for_category(keys[combobox.get_active()])
        else :
            for i in range(len(self.entries)) :
                self.entries[i].set_text("")
                self.highlight_tag(i, False)
            self.current_category = None

        return True

    def next_category(self, howmany) :
        '''Advance to the next category (if howmany==1) or some other category.
        '''
        keys = self.categories.keys()
        catno = keys.index(self.current_category)
        catno = (catno + howmany) % len(keys)
        print "Advancing by", howmany, "to", keys[catno]
        self.show_category_by_number(catno)

    def show_category_by_number(self, catno) :
        '''Show a specific category by number.
           Raises IndexError if catno is out of range.
        '''
        self.display_tags_for_category(self.categories.keys()[catno])
        self.categorysel.set_active(catno)

    def update_edited_category(self) :
        '''The user may have edited the current category name,
           or changed *** add new *** to an actual
           category name. If so, we need to update our changes.
           We can't base this on the active combobox entry, since
           it may be called when the user switches to another entry.
        '''
        print "update edited category"
        # self.current_category = combobox.get_active_text()
        print "New text is:", self.categorysel.get_active_text()

        try :
            oldcatno = self.categories.keys().index(self.current_category)
            print "Old name was", self.current_category
            if self.current_category == self.categorysel.get_active_text() :
                return
            self.rename_category(self.current_category,
                                 self.categorysel.get_active_text())
            print "categories now look like:", self.categories
        except ValueError :
            oldcatno = -1
            print "Didn't have an old name"

    def highlight_tag(self, tagno, val) :
        '''Turn tag number tagno on (if val=True) or off (val=False).'''

        if self.buttons[tagno].get_active() != val :
            self.ignore_events = True
            self.buttons[tagno].set_active(val)
            self.ignore_events = False

        if val :
            self.entries[tagno].modify_base(gtk.STATE_NORMAL, self.highlight_bg)
            # If a tag is highlighted and the associated entry is empty,
            # put focus there so the user can type something.
            if not self.entries[tagno].get_text().strip() :
                self.parentwin.set_focus(self.entries[tagno])
        else :
            self.entries[tagno].modify_base(gtk.STATE_NORMAL, self.greyBG)
            if self.parentwin.get_focus() == self.entries[tagno] :
                self.focus_none()

    def show_matches(self, pat) :
        '''Colorize any tags that match the given pattern.
           If pat == None, un-colorize everything.
        '''
        if pat :
            self.title.set_text("search: " + pat)
        else :
            self.title.set_text(os.path.basename(self.cur_img.filename))
        pat = pat.lower()
        for i, ent in enumerate(self.entries) :
            if pat and (ent.get_text().lower().find(pat) >= 0) :
                ent.modify_base(gtk.STATE_NORMAL, self.matchBG)
            elif self.buttons[i].get_active() :
                ent.modify_base(gtk.STATE_NORMAL, self.highlight_bg)
            else :
                ent.modify_base(gtk.STATE_NORMAL, self.greyBG)

    def focus_first_match(self, pat) :
        '''Focus the first text field matching the pattern.'''
        self.title.set_text(os.path.basename(self.cur_img.filename))
        pat = pat.lower()
        for i, ent in enumerate(self.entries) :
            if pat and (ent.get_text().lower().find(pat) >= 0) :
                self.buttons[i].set_active(True)
                ent.modify_base(gtk.STATE_NORMAL, self.matchBG)
                return

    def set_image(self, img) :
        self.cur_img = img

        self.title.set_text(os.path.basename(img.filename))

        self.display_tags_for_category(self.current_category)

        return

    def add_tag(self, tag, img) :
        '''Add a tag to the given image.
           img is a MetaPho.Image.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index (in the global tags list) of the tag just added,
           or None if error.
        '''
        # Call the base class to make sure the tag is there:
        tagindex = MetaPho.Tagger.add_tag(self, tag, img)

        # Now display it, if possible
        if tagindex < len(self.entries) :
            self.highlight_tag(tagindex, True)

        return tagindex

    def remove_tag(self, tag, img) :
        if not type(tag) is int :
            tagstr = tag
            tag = self.tag_list.index(tagstr)
            if tagstr < 0 :
                print "No such tag", tagstr
                return

        MetaPho.Tagger.remove_tag(self, tag, img)

        self.highlight_tag(tag, False)

    def toggle_tag(self, tagno, img) :
        '''Toggle tag number tagno for the given img.'''
        MetaPho.Tagger.toggle_tag(self, tagno, img)
        if tagno < len(self.entries) :
            self.highlight_tag(tagno, not self.buttons[tagno].get_active())

    def toggle_tag_by_letter(self, tagchar, img) :
        '''Toggle the tag corresponding to the letter typed by the user'''
        if tagchar.islower() :
            tagno = ord(tagchar) - ord('a')
        else :
            tagno = ord(tagchar) - ord('A') + self.num_rows
        self.toggle_tag(tagno, img)

    def focus_next_entry(self) :
        '''Set focus to the next available entry.
           If we're already typing in a new tag entry that hasn't been
           saved yet, save it first before switching to the new one.
        '''
        newindex = len(self.categories[self.current_category])

        # No need to save this entry's new contents explicitly;
        # when we call highlight_tag it'll get a focus out which
        # will automatically save. But we do need to increment newindex
        # if the user typed anything here.

        curtext = self.entries[newindex].get_text()
        if curtext.strip() != '' :
            newindex += 1

        self.parentwin.set_focus(self.entries[newindex])
        self.highlight_tag(newindex, True)

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

            # Have we had load_image called, but we weren't ready for it?
            # Now, theoretically, we are ... so call it again.
            if self.cur_img and not self.pixbuf :
                self.load_image(self.cur_img)

        self.show_image()

    # Mapping from EXIF orientation tag to degrees rotated.
    # http://sylvana.net/jpegcrop/exif_orientation.html
    exif_rot_table = [ 0, 0, 180, 180, 270, 270, 90, 90 ]
    # Note that orientations 2, 4, 5 and 7 also involve a flip.
    # We're not implementing that right now, because nobody
    # uses it in practice.

    def load_image(self, img) :
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

            self.show_image()
            loaded = True

        except glib.GError :
            self.pixbuf = None
            loaded = False

        # garbage collect the old pixbuf, if any, and the one we just read in:
        newpb = None
        gc.collect()

        return loaded

    def show_image(self) :
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
        self.load_image(self.cur_img)

