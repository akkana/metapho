#!/usr/bin/env python

'''
GTK UI classes for metapho: an image tagger and viewer.
'''

# Copyright 2013 by Akkana Peck: share and enjoy under the GPL v2 or later.

import metapho

import gtk
import gc
import glib, gobject
import os
import collections

class TagViewer(metapho.Tagger, gtk.Table) :
    '''A PyGTK widget for showing tags.
    '''
    def __init__(self, parentwin) :
        metapho.Tagger.__init__(self)
        self.num_rows = 26
        gtk.Table.__init__(self, 4, self.num_rows, False)

        self.parentwin = parentwin

        self.title = gtk.Label("Tags")
        self.attach(self.title, 0, 4, 0, 1 )

        self.catviewer = CategoryViewer(3, self.change_cat_cb)
        self.attach(self.catviewer, 0, 4, 1, 2)
        self.catviewer.show()

        # hbox = gtk.HBox()
        # hbox.pack_start(gtk.Label("Tag category:"), expand=False)

        # edit_btn = gtk.Button("Edit")
        # edit_btn.connect("clicked", self.edit_categories)
        # hbox.pack_end(edit_btn, expand=False)
        # edit_btn.unset_flags(gtk.CAN_FOCUS)

        # # Set up a combobox with a text entry, so the user can change cats.
        # # To make it editable is immensely more complicated than just
        # # calling gtk.combo_box_entry_new_text(); thanks to Juhaz on #pygtk
        # # for an example of how to set it up.
        # # self.categorysel = gtk.combo_box_entry_new_text()
        # self.cat_list_store = gtk.ListStore(str)
        # self.categorysel = gtk.ComboBox(self.cat_list_store)
        # # self.categorysel = gtk.ComboBoxEntry(self.cat_list_store, 0)
        # cr = gtk.CellRendererText()
        # self.categorysel.pack_start(cr)
        # self.categorysel.set_attributes(cr, text=0)
        # # Try to keep focus out of the combobox -- but it's not possible.
        # self.categorysel.unset_flags(gtk.CAN_FOCUS)

        # hbox.pack_start(self.categorysel, expand=True)

        # self.attach(hbox, 0, 4, 1, 2 )

        self.cur_img = None
        self.highlight_bg = gtk.gdk.color_parse("#FFFFFF")
        self.greyBG = gtk.gdk.color_parse("#DDDDDD")
        self.matchBG = gtk.gdk.color_parse("#DDFFEE")
        self.ignore_events = False

        self.editing = False

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
                self.attach(button, left, left+1, i+2, i+3 )
                self.buttons.append(button)
                button.connect("toggled", self.toggled, len(self.entries))

                entry = gtk.Entry()
                entry.set_width_chars(25)
                #entry.connect("changed", self.entry_changed, i)
                #entry.connect("focus-in-event", self.focus_in, i)
                entry.connect("focus-out-event", self.focus_out,
                              len(self.entries))
                self.attach(entry, left+1, left+2, i+2, i+3 )
                self.entries.append(entry)

        self.show()

    def change_cat_cb(self, cat):
        print "Clicked on", cat

    def change_tag(self, tagno, newstr) :
        '''Update a tag: called on focus_out from one of the text entries'''
        if tagno < len(self.categories[self.current_category]) :
            self.tag_list[self.categories[self.current_category][tagno]] = newstr
        else :
            newtag = self.add_tag(newstr, self.cur_img)
            self.highlight_tag(newtag, True)

    def clear_tags(self, img) :
        metapho.Tagger.clear_tags(self, img)

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
        if self.categories :
            for catname in self.categories.keys() :
                # self.cat_list_store.append((catname,))
                self.catviewer.add_category(catname)
        else :
            # self.cat_list_store.append((self.current_category,))
            self.catviewer.add(self.current_category)

        # Set the first category as current, and display its tags.
        if self.categories :
            self.current_category = self.categories.keys()[0]
        # else the current category should still be at the default.
        self.display_tags_for_category(self.current_category)

        self.catviewer.set_active(0)

        # self.categorysel.connect("changed", self.change_category)
        # XXX hook up categorysel buttons

    def display_tags_for_category(self, catname) :
        print "display_tags_for_category(%s)" % catname
        # Is this a new category, not in the list?
        if catname not in self.categories.keys() :
            print catname, "was not in the category list"
            for i in range(len(self.entries)) :
                self.entries[i].set_text("")
                self.highlight_tag(i, False)
            return

        if self.cur_img and self.cur_img.tags :
            cur_img_tags = []
            for i in self.cur_img.tags :
                try :
                    cur_img_tags.append(self.tag_list[i])
                except IndexError :
                    print i, "is out of range, we only have", \
                        len(self.tag_list), "tags"
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
        '''The callback when the combobox is changed by the user'''
        self.display_tags_for_category(combobox.get_active_text())

    def next_category(self, howmany) :
        '''Advance to the next category (if howmany==1) or some other category.
        '''
        keys = self.categories.keys()
        catno = keys.index(self.current_category)
        catno = (catno + howmany) % len(keys)
        self.show_category_by_number(catno)

    def show_category_by_number(self, catno) :
        '''Show a specific category by number.
           Raises IndexError if catno is out of range.
        '''
        self.display_tags_for_category(self.categories.keys()[catno])
        self.catviewer.set_active(catno)

    def edit_categories(self, w) :
        d = gtk.Dialog('Edit categories', self.parentwin,
                       buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CLOSE,
                                gtk.STOCK_OK, gtk.RESPONSE_OK))
        d.set_default_size(300, 500)

        v = gtk.VBox()

        self.edit_cell = None
        self.edit_path = None

        def category_edited(cr, path, text):
            self.cat_list_store[path][0] = text

        def get_cell(cr, editable, path) :
            self.edit_cell = editable
            self.edit_path = path

        t = gtk.TreeView(self.cat_list_store)
        cr = gtk.CellRendererText()
        cr.props.editable = True
        cr.connect('edited', category_edited)
        cr.connect('editing_started', get_cell)
        # Don't handle editing_canceled because it will be called on OK.
        # cr.connect('editing_canceled', clear_cell)

        col = gtk.TreeViewColumn('Category', cr, text=0)
        t.insert_column(col, -1)

        sw = gtk.ScrolledWindow()
        sw.add(t)
        v.add(sw)

        def save_current() :
            if self.edit_cell and self.edit_path :
                self.cat_list_store[self.edit_path][0] = \
                    self.edit_cell.get_text()

        def add_category(b):
            save_current()
            self.cat_list_store.append(('New category',))
            t.set_cursor(self.cat_list_store[-1].path, col, True)

        b = gtk.Button('Add...')
        b.connect('clicked', add_category)
        v.pack_start(b, False, False)

        d.get_content_area().add(v)

        d.show_all()

        while gtk.events_pending():
            gtk.main_iteration(False)

        response = d.run()
        if response == gtk.RESPONSE_OK :
            save_current()

            # Update the category list to reflect the new names.
            # Since it's an OrderedDict, we can't just replace keys,
            # we have to build a whole new dict.
            # Save keys and position of current category:
            oldkeys = self.categories.keys()
            old_cur_pos = oldkeys.index(self.current_category)
            i = 0

            newcats = collections.OrderedDict()

            # Iterate over the list that was in the dialog
            # and is now in the combobox:
            iter = self.cat_list_store.get_iter_first()
            while iter:
                item = self.cat_list_store.get_value(iter, 0)
                if i < len(oldkeys) :
                    newcats[item] = self.categories[oldkeys[i]]
                else :
                    newcats[item] = []
                if i == old_cur_pos :
                    self.current_category = item
                iter = self.cat_list_store.iter_next(iter)
                i += 1

            self.categories = newcats
            if self.current_category > i :
                self.current_category = 0
            self.show_category_by_number(self.current_category)

        d.destroy()

        self.focus_none()

    def highlight_tag(self, tagno, val) :
        '''Turn tag number tagno on (if val=True) or off (val=False).'''

        if len(self.buttons) < tagno :
            print "Argh! Tried to highlight tag", tagno
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

        # Update the category viewer
        # self.catviewer.set_image(img, self.current_category)

        return

    def add_tag(self, tag, img) :
        '''Add a tag to the given image.
           img is a metapho.Image.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index (in the global tags list) of the tag just added,
           or None if error.
        '''
        # Call the base class to make sure the tag exists:
        tagindex = metapho.Tagger.add_tag(self, tag, img)

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

        metapho.Tagger.remove_tag(self, tag, img)

        self.highlight_tag(tag, False)

    def toggle_tag(self, tagno, img) :
        '''Toggle tag number tagno for the given img.'''
        metapho.Tagger.toggle_tag(self, tagno, img)
        if tagno < len(self.categories[self.current_category]) :
            self.highlight_tag(tagno, not self.buttons[tagno].get_active())

    def toggle_tag_by_letter(self, tagchar, img) :
        '''Toggle the tag corresponding to the letter typed by the user'''
        if tagchar.islower() :
            tagno = ord(tagchar) - ord('a')
        else :
            tagno = ord(tagchar) - ord('A') + self.num_rows
        if tagno >= len(self.tag_list) :
            print "We don't have a tag", tagchar, "yet"
            return
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

class CategoryViewer(gtk.Table):
    '''Display the categories known so far, and some indication of
       in which categories the current image has tags.
       The last button should always be a "New Category" button.
       When category buttons are pressed, they'll call the callback
       you pass in, which has signature: change_cat_cb(self, cat)

    '''
    add_cat_string = "Add Category"
    def __init__(self, ncols, callback=None):
        self.categories = []
        self.buttons = []
        self.ncols = ncols
        self.callback = callback

        # GTK has no sensible way of ignoring generated events
        # vs. events the user caused by clicking on something.
        # So maintain a variable we can use when we're updating the buttons,
        # so each update doesn't cause a cascade of recursive updates.
        # I so love GTK.
        self.updating = False

        super(CategoryViewer, self).__init__(1, 1, True)

        self.add_cat_btn = gtk.ToggleButton(CategoryViewer.add_cat_string)
        self.attach(self.add_cat_btn, 0, 1, 0, 1)
        self.add_cat_btn.show()

        # Color to highlight and unhighlight buttons.
        # We can't get these until we've created a button.
        widgcopy = self.add_cat_btn.get_style().copy()
        self.oldcolors = widgcopy.bg
        self.highlightcolor = gtk.gdk.Color(0, 65535, 0)

    def add_category(self, newcat):
        if newcat in self.categories:
            print newcat, "is already a category"
            return
        curcat = len(self.categories)
        oldrow, oldcol = divmod(curcat, self.ncols)
        newrow, newcol = divmod(curcat+1, self.ncols)

        # Move the add_cat_btn to the next spot:
        self.remove(self.add_cat_btn)
        self.attach(self.add_cat_btn, newcol, newcol + 1, newrow, newrow + 1)

        # Make a new button where the add_cat_btn was:
        btn =  gtk.ToggleButton(newcat)
        self.attach(btn, oldcol, oldcol + 1, oldrow, oldrow + 1)
        btn.show()
        btn.connect("toggled", self.button_cb, curcat)

        self.buttons.append(btn)
        self.categories.append(newcat)

    def button_cb(self, w, which):
        if self.updating:
            return
        # print "Clicked on", which
        self.set_active(which)
        if self.callback:
            self.callback(self.categories[which])

    def getwhich(self, which):
        if isinstance(which, int):
            return which, self.categories[which]

        # else presumably it's a string.
        try:
            i = self.categories.index(which)
        except ValueError:
            print "No such category", savecat
            return None, which
        return i, which

    def set_active(self, which):
        '''Make a given category active, by name or index.'''
        which, catname = self.getwhich(which)

        # Now which should be int.
        self.updating = True
        for i, btn in enumerate(self.buttons):
            btn.set_active(i == which)
            self.set_highlight(btn, i == which)
        self.updating = False

    def set_highlight(self, which, highlight):
        '''Highlight or unhighlight a button, by reference, index or name'''
        if isinstance(which, int):
            btn = self.buttons[which]
        elif isinstance(which, str):
            which, catname = self.getwhich(which)
        else:
            btn = which

        if highlight:
            btn.modify_bg(gtk.STATE_NORMAL, self.highlightcolor)
            btn.modify_bg(gtk.STATE_ACTIVE, self.highlightcolor)
            btn.modify_bg(gtk.STATE_PRELIGHT, self.highlightcolor)
            btn.modify_bg(gtk.STATE_SELECTED, self.highlightcolor)
        else:
            btn.modify_bg(gtk.STATE_NORMAL, self.oldcolors[gtk.STATE_NORMAL])
            btn.modify_bg(gtk.STATE_ACTIVE, self.oldcolors[gtk.STATE_ACTIVE])
            btn.modify_bg(gtk.STATE_PRELIGHT,
                          self.oldcolors[gtk.STATE_PRELIGHT])
            btn.modify_bg(gtk.STATE_SELECTED,
                          self.oldcolors[gtk.STATE_SELECTED])

if __name__ == '__main__':
    w = gtk.Window(gtk.WINDOW_TOPLEVEL)
    catviewer = CategoryViewer(3)
    w.add(catviewer)
    catviewer.show()
    for c in ["Animals", "Plants", "Natural Features",
              "Architecture", "Atmospheric"]:
        catviewer.add_category(c)
    w.show()
    gtk.main()

class ImageViewer(gtk.DrawingArea) :
    '''A PyGTK image viewer widget for metapho.
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
           img is a metapho.Image object.
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
