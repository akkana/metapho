#!/usr/bin/env python

"""
GTK UI classes for metapho: an image tagger and viewer.
"""

# Copyright 2013-2021 by Akkana Peck: share and enjoy under the GPL v2 or later.

from __future__ import print_function

import metapho

from gi import pygtkcompat
pygtkcompat.enable()
pygtkcompat.enable_gtk(version='3.0')

import gtk
import os
import collections
import traceback


class TagViewer(metapho.Tagger, gtk.Table):
    """A PyGTK widget for showing tags.
    """
    def __init__(self, parentwin):
        metapho.Tagger.__init__(self)
        self.num_rows = 26
        gtk.Table.__init__(self, 4, self.num_rows, False)

        self.parentwin = parentwin

        self.title = gtk.Label("Tags")
        self.attach(self.title, 0, 4, 0, 1 )

        self.cur_img = None

        # The Byzantine GTK3 way of changing background color:
        self.provider = gtk.CssProvider()
        # Load the CSS
        # Note: GTK doesn't understand 3-digit colors like #fff
        self.provider.load_from_data(b"""
  .normal        { background-color: #eeeeee; }
  .highlighted   { background-color: #ffffff; }
  .matched       { background-color: #ddffdd; }
  button         { background:       #cccccc; }
  button:checked { background:       #f8f8ff; }
        """)
        gtk.StyleContext.add_provider_for_screen(gtk.gdk.Screen.get_default(),
                                                 self.provider,
                                  gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.ignore_events = False

        # GTK foo that will be needed if we ever edit categories:
        self.cat_list_store = None

        # The category viewer, on the upper right
        self.catviewer = CategoryViewer(3,
                                        change_cat_cb=self.change_category,
                                        new_cat_cb=self.edit_categories)
        self.attach(self.catviewer, 0, 4, 1, 2)
        self.catviewer.show()

        self.editing = False

        # Set up a bunch of entries, also setting the table size:
        self.buttons = []
        self.entries = []
        self.button_names = []
        for j in range(0, 2):
            for i in range(0, self.num_rows):
                if j <= 0:
                    buttonchar = chr(i + ord('a'))
                    left = 0
                else:
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
                entry.get_style_context().add_class("normal")

                entry.connect("focus-out-event", self.focus_out,
                              len(self.entries))

                self.attach(entry, left+1, left+2, i+2, i+3 )
                self.entries.append(entry)

        self.show()

    def change_tag(self, entryno, newstr):
        """Update a tag: called on focus_out from one of the text entries"""

        # Number of tags in this category:
        numtags = len(self.categories[self.current_category])

        newstr = newstr.strip()

        # If the string is now empty, and it's the last tag
        # in both this category and the overall tag list,
        # remove it from the tag list, the category and the current image.
        # XXX Note that other images may still refer to this
        # nonexistent tag. Possibly we should consider looping through
        # the whole image list.
        if not newstr:
            if entryno == numtags-1:
                tag_list_no = self.categories[self.current_category][entryno]
                if entryno == numtags - 1 and tag_list_no == len(self.tag_list) - 1:
                    tagno = self.categories[self.current_category].pop(-1)
                    self.tag_list.pop(-1)
                    try:
                        index = self.cur_img.tags.index(tagno)
                        self.cur_img.tags.pop(index)
                    except ValueError:
                        pass

        # If it's changing an existing tag, just do it.
        elif entryno < numtags:
            self.tag_list[self.categories[self.current_category][entryno]] \
                = newstr

        # The string is nonempty and doesn't change an existing tag,
        # so add a new tag.
        else:
            self.add_tag(newstr, self.cur_img)

    def clear_tags(self, img):
        """Clear all tags from the current image.
        """
        metapho.Tagger.clear_tags(self, img)

        # leave nothing focused
        self.focus_none()

        # also update the UI
        for i in range(len((self.entries))):
            self.highlight_tag(i, False)
        self.catviewer.unhighlight_all()

    def focus_none(self):
        """Un-focus any currently focused text entry,
           leaving nothing focused.
           If there was a focused entry and it was empty,
           de-highlight the corresponding toggle button.
        """
        # Make sure we're leaving nothing focused:
        self.parentwin.set_focus(None)

    def sync_entry(self, entry, entryno):
        entry_text = entry.get_text()
        self.change_tag(entryno, entry_text)

    def sync(self):
        """Update tags to reflect the contents of the current entry.
           Called on things like next_image and quit.
        """
        entry = self.parentwin.get_focus()
        # Everybody says to use isinstance, but to do that you need
        # another variable to check against None because None
        # has no isinstance().
        if type(entry) is not gtk.Entry:
            return

        # Get the focused entry's number
        entryno = None
        for i, e in enumerate(self.entries):
            if entry == e:
                self.sync_entry(entry, i)
                self.focus_none()
                return
        print("can't get the focused entry number")

    def focus_out(self, entry, event, entryno):
        """Called when a text entry loses focus."""
        # We need to update the tags when a text entry is defocused,
        # but we don't want to do that every time the whole window
        # loses focus. Detect that case:
        winfocused = self.parentwin.get_focus()
        if winfocused == entry:
            print("The window was unfocused, not the entry within the window")
            return

        # I think ??? this should always be true
        if entry == self.entries[entryno]:
            self.sync_entry(entry, entryno)
            return True

        # Just in case that assumption is wrong, search for it.
        for i, e in enumerate(self.entries):
            if entry == e:
                print("eek, entry is", entry, "and e is", e)
                self.sync_entry(entry, entryno)
                return True

        # print("Didn't find the focused entry")
        return True

    def toggled(self, button, btnno):
        """Called when clicking on either a tag button or a category button.
        """
        # We'll get a recursion loop if we don't block events here --
        # adding and removing tags update the GUI state, which
        # changes the toggle button state, which calls toggled() again.

        if self.ignore_events:
            return

        numtags = len(self.categories[self.current_category])
        if btnno >= numtags:
            print("button number too big!", btnno)
            return

        elif self.categories:
            tagno = self.categories[self.current_category][btnno]
        else:
            tagno = None

        # get_active() is the state *after* the button has been pressed.
        if button.get_active():
            # Was off, now on, so add the tag.
            # But not if the tag doesn't exist yet.
            if tagno:
                self.add_tag(tagno, self.cur_img)
            self.highlight_tag(btnno, True)
        else:
            # It's already on, so toggle it off.
            # But not if the tag doesn't exist yet.
            if tagno:
                self.remove_tag(tagno, self.cur_img)
            self.highlight_tag(btnno, False)

        # Often when the user clicks on a button it's because
        # focus was in a text field. We definitely don't want it
        # to stay there.
        self.focus_none()

        return True

    def check_entry_tag(focused_widget):
        """At certain times, such as just before exit, the main window
           may call us to alert us that a tag may have changed.
           We need to find out which entry contains it and check the tag.
        """
        for i, ent in enumerate(self.entries):
            if focused_widget == ent:
                self.focus_out(ent, None, i)

    def display_tags(self):
        """Called after read_tags() has been read for all directories."""

        # Add our categories to the combo.
        if self.categories:
            for catname in list(self.categories.keys()):
                self.catviewer.add_category(catname)
        else:
            self.catviewer.add_category(self.current_category)

        # Set the first category as current, and display its tags.
        if self.categories:
            self.current_category = list(self.categories.keys())[0]
        # else the current category should still be at the default.

        self.display_tags_for_category(self.current_category)

    def display_tags_for_category(self, catname):
        """Display the tag names in a new category,
           and reset the mapping.
        """
        # Is this a new category, not in the list?
        if catname not in list(self.categories.keys()):
            for i in range(len(self.entries)):
                self.entries[i].set_text("")
                self.highlight_tag(i, False)
            return

        if self.cur_img and self.cur_img.tags:
            cur_img_tags = []
            for i in self.cur_img.tags:
                try:
                    cur_img_tags.append(self.tag_list[i])
                except IndexError:
                    print(i, "is out of range, we only have space for", \
                        len(self.tag_list))
                    print("img", self.cur_img)
                    print("img.tags:", self.cur_img.tags)
        else:
            cur_img_tags = []
        self.current_category = catname
        for i in range(len(self.entries)):
            if i < len(self.categories[catname]):
                curtag = self.tag_list[self.categories[catname][i]]
                self.entries[i].set_text(curtag)
                self.highlight_tag(i, curtag in cur_img_tags)

            else:
                self.entries[i].set_text("")
                self.highlight_tag(i, False)

        if len(self.categories[catname]) > len(self.entries):
            print("Too many tags in category %s -- can't show all %d" % \
                (catname, len(self.categories[catname])))

    # XXX This is broken.
    def highlight_categories(self):
        """Highlight the button for any category that includes tags
           set in this image.
        """
        # self.catviewer.unhighlight_all()
        # for tag in self.cur_img.tags:
        #     for cat in self.categories:
        #         if tag in self.categories[cat]:
        #             self.catviewer.set_highlight(cat, True)
        return

    def change_category(self, cat):
        """The callback when the category is changed by the user"""
        self.display_tags_for_category(cat)

    def next_category(self, howmany):
        """Advance to the next category (if howmany==1) or some other category.
        """
        keys = list(self.categories.keys())
        catno = keys.index(self.current_category)
        catno = (catno + howmany) % len(keys)
        self.show_category_by_number(catno)

    def show_category_by_number(self, catno):
        """Show a specific category by number.
           Raises IndexError if catno is out of range.
        """
        self.display_tags_for_category(list(self.categories.keys())[catno])
        self.catviewer.set_active(catno)

    def edit_categories(self, w):
        d = gtk.Dialog('New category', self.parentwin,
                       buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CLOSE,
                                gtk.STOCK_OK, gtk.RESPONSE_OK))

        # OK is the default response:
        d.set_default_response(gtk.RESPONSE_OK)

        vbox = gtk.VBox(spacing=4)
        d.get_content_area().add(vbox)

        label = gtk.Label("New category:")
        vbox.pack_start(label)
        entry = gtk.Entry()
        entry.set_width_chars(25)
        entry.set_activates_default(True)
        vbox.pack_start(entry)
        label = gtk.Label("")
        vbox.pack_start(label)

        d.show_all()

        while True:
            response = d.run()
            # Escape gives a response of -4 (DELETE_EVENT)
            if response == gtk.RESPONSE_CLOSE \
               or response == gtk.RESPONSE_DELETE_EVENT:
                break
            if response == gtk.RESPONSE_OK:
                newcat = entry.get_text()
                if not newcat:
                    label.set_text("Specify a new category, or Cancel")
                    continue
                if newcat in self.categories:
                    label.set_text("%s already exists" % newcat)
                    continue
                self.categories[newcat] = []
                self.catviewer.add_category(newcat)
                break

        d.destroy()

        self.focus_none()

    def highlight_tag(self, tagno, val):
        """Turn tag number tagno on (if val=True) or off (val=False)."""

        # if val:
        #     print("\n======== highlight_tag", tagno)
        #     traceback.print_stack()

        if len(self.buttons) < tagno:
            print("Argh! Tried to highlight too big a tag", tagno,
                  "but can only show", len(self.buttons))
            return

        # If the last entry is expected to be higlighted,
        # but it's empty, the user probably just deleted the tag.
        # Remove that tag from the image and the tag list.
        if val and not self.entries[tagno].get_text().strip() \
           and tagno == len(self.categories[self.current_category]) - 1:
            self.parentwin.set_focus(self.entries[tagno])
            # Remove it from the image:
            self.remove_tag(tagno, self.cur_img)

        self.ignore_events = True
        if val:
            self.buttons[tagno].set_active(True)
        else:
            self.buttons[tagno].set_active(False)
            if self.parentwin.get_focus() == self.entries[tagno]:
                self.focus_none()
        self.ignore_events = False

        # Set the color of the corresponding text entry
        if val:
            self.highlight_entry(self.entries[tagno], "highlighted")
        else:
            self.highlight_entry(self.entries[tagno])

    def highlight_entry(self, entry, classname=None):
        context = entry.get_style_context()
        context.remove_class("highlighted")
        context.remove_class("matched")
        if classname:
            context.add_class(classname)

    def highlight_entries(self, pat=None):
        """Highlight all the entries, with a special color for any tags
           that match the given pattern.
        """
        if not self.cur_img:
            print("highlight_entries called too early")
            return
        if pat:
            self.title.set_text("search: " + pat)
            pat = pat.lower()
        else:
            self.title.set_text(os.path.basename(self.cur_img.filename))

        for i, ent in enumerate(self.entries):
            if pat and (ent.get_text().lower().find(pat) >= 0):
                self.highlight_entry(ent, "matched")
            elif self.buttons[i].get_active():
                self.highlight_entry(ent, "highlighted")
            else:
                self.highlight_entry(ent)

    def focus_first_match(self, pat):
        """Focus the first text field matching the pattern."""
        self.title.set_text(os.path.basename(self.cur_img.filename))
        pat = pat.lower()
        for i, ent in enumerate(self.entries):
            if pat and (ent.get_text().lower().find(pat) >= 0):
                self.buttons[i].set_active(True)
                self.highlight_entry(ent, "matched")
                return

    def img_has_tags_in(self, img, cat):
        for tag in img.tags:
            if tag in self.categories[cat]:
                return True

    def set_image(self, img):
        self.cur_img = img

        self.title.set_text(os.path.basename(img.filename))

        # Decide what category to show.
        # If the image has tags set in the current category,
        # or the image has no tags set in any category,
        # leave the current category unchanged.
        # Otherwise, switch to the first category where this image has tags.
        if img.tags and not self.img_has_tags_in(img, self.current_category):
            for cat in self.categories:
                if self.img_has_tags_in(img, cat):
                    self.current_category = cat
                    break

        self.catviewer.set_active(self.current_category)
        self.highlight_categories()
        self.display_tags_for_category(self.current_category)

        return

    def add_tag(self, tag, img):
        """Add a tag to the given image.
           img is a metapho.Image.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index (in the global tags list) of the tag just added,
           or None if error.
        """
        # Call the base class to make sure the tag exists:
        tagindex = metapho.Tagger.add_tag(self, tag, img)

        # Now display it, if possible
        # print "highlighting from add_tag(%s)" % tag

        # tagindex is the index (in the global tags list) of the tag
        # just added, which has nothing (necessarily) to do with the
        # index of the entry in our window, so highlighting based on
        # that is just wrong.
        # (It might accidentally work in cases with no categories.)
        # if tagindex < len(self.entries):
        #     self.highlight_tag(tagindex, True)

        return tagindex

    def remove_tag(self, tag, img):
        if not type(tag) is int:
            tagstr = tag
            tag = self.tag_list.index(tagstr)
            if tagstr < 0:
                print("No such tag", tagstr)
                return

        metapho.Tagger.remove_tag(self, tag, img)

    def toggle_tag(self, btnno, img):
        """Toggle tag number tagno for the given img."""
        if btnno < len(self.categories[self.current_category]):
            tagno = self.categories[self.current_category][btnno]

            if tagno >= len(self.tag_list):
                # I think this shouldn't happen given the btnno check,
                # so print a warning if it does.
                print("Eek: tagno is", tagno, "len tag_list is", \
                    len(self.tag_list))
                return

            metapho.Tagger.toggle_tag(self, tagno, img)

        if btnno < len(self.buttons) and \
           btnno <= len(self.categories[self.current_category]):
            # Note <= comparison where previously we looked for <.
            # We'll highlight the tag if it's an existing tag or if
            # it's the first new tag, but not arbitrary higher new tags.
            self.highlight_tag(btnno, not self.buttons[btnno].get_active())

    def toggle_tag_by_letter(self, tagchar, img):
        """Toggle the tag corresponding to the letter typed by the user"""
        if tagchar.islower():
            btnno = ord(tagchar) - ord('a')
        else:
            btnno = ord(tagchar) - ord('A') + self.num_rows
        self.toggle_tag(btnno, img)

    def focus_next_entry(self):
        """Set focus to the next available entry (user just hit Enter).
           If we're already typing in a new tag entry that hasn't been
           saved yet, save it first before switching to the new one.

           When testing this, try:
           - erase what's in the last entry, then hit Enter:
             should go to the entry just erased
           - erase what's in the last entry, then click in another
             entry, then hit Enter:
             should go to the entry just erased
        """
        # If focus is currently in an entry, force it to unfocus,
        # which will force an update of the tags list.
        self.focus_none()

        # First time for this category, no entries filled yet
        if not self.categories[self.current_category]:
            newindex = 0

        else:
            # First check whether the entry corresponding to the last tag
            # is empty, e.g. if the user accidentally entered something
            # and then tried to erase it.
            newindex = len(self.categories[self.current_category]) - 1
            curtext = self.entries[newindex].get_text().strip()
            if curtext:
                # There's something there, so jump to the next entry.
                newindex += 1

        self.parentwin.set_focus(self.entries[newindex])
        self.highlight_tag(newindex, True)


class CategoryViewer(gtk.Table):
    """Display the categories known so far, and some indication of
       in which categories the current image has tags.
       The last button should always be a "New Category" button.
       When category buttons are pressed, they'll call the callback
       you pass in, which has signature: change_cat_cb(cat).
       The caller can also pass in a new_cat_cb (which takes no args)
       where it can offer a way to create a new category.
    """
    add_cat_string = "Add Category"

    def __init__(self, ncols, change_cat_cb=None, new_cat_cb=None,
                 highlight_color=None):
        self.categories = []
        self.buttons = []
        self.ncols = ncols
        self.change_cat_cb = change_cat_cb

        # GTK has no sensible way of ignoring generated events
        # vs. events the user caused by clicking on something.
        # So maintain a variable we can use when we're updating the buttons,
        # so each update doesn't cause a cascade of recursive updates.
        # I so love GTK.
        self.updating = False

        super(CategoryViewer, self).__init__(1, 1, True)

        self.add_cat_btn = gtk.Button(CategoryViewer.add_cat_string)
        self.attach(self.add_cat_btn, 0, 1, 0, 1)
        self.add_cat_btn.show()
        if new_cat_cb:
            self.add_cat_btn.connect("clicked", new_cat_cb)

    def add_category(self, newcat):
        if newcat in self.categories:
            return
        curcat = len(self.categories)
        oldrow, oldcol = divmod(curcat, self.ncols)
        newrow, newcol = divmod(curcat+1, self.ncols)

        # Move the add_cat_btn to the next spot:
        self.remove(self.add_cat_btn)
        self.attach(self.add_cat_btn, newcol, newcol + 1, newrow, newrow + 1)

        # Make a new button where the add_cat_btn was:
        btn =  gtk.ToggleButton(str("%d: %s" % (curcat, newcat)))
        self.attach(btn, oldcol, oldcol + 1, oldrow, oldrow + 1)
        btn.show()
        btn.connect("toggled", self.button_cb, curcat)

        self.buttons.append(btn)
        self.categories.append(newcat)

    def button_cb(self, w, which):
        if self.updating:
            return
        self.set_active(which)
        if self.change_cat_cb:
            self.change_cat_cb(self.categories[which])

    def getwhich(self, which):
        if isinstance(which, int):
            return which, self.categories[which]

        # else presumably it's a string.
        try:
            i = self.categories.index(which)
        except ValueError:
            print("No such category", savecat)
            return None, which
        return i, which

    def set_active(self, which):
        """Make a given category active, by name or index."""
        which, catname = self.getwhich(which)

        # Now which should be int.
        self.updating = True
        for i, btn in enumerate(self.buttons):
            btn.set_active(i == which)
        self.updating = False

    def set_highlight(self, which, highlight):
        """Highlight or unhighlight a button, by reference, index or name"""
        if isinstance(which, int):
            btn = self.buttons[which]
        elif isinstance(which, str):
            which, catname = self.getwhich(which)
            btn = self.buttons[which]
        else:
            btn = which

        self.ignore_events = True
        btn.set_active(highlight)
        self.ignore_events = False

    def unhighlight_all(self):
        for btn in self.buttons:
            self.set_highlight(btn, False)


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
