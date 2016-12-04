#!/usr/bin/env python

# metapho: an image tagger and viewer.

# Copyright 2013 by Akkana Peck: share and enjoy under the GPL v2 or later.

from . import MetaPho
from . import gtkpho

import gtk

import sys, os

import traceback

class MetaPhoWindow(object):
    '''The main controller window for MetaPho.
       This holds any child widgets, like the image viewer and tags window,
       and manages key events and other user commands.
    '''

    def __init__(self, file_list):
        for filename in file_list:
            MetaPho.Image.g_image_list.append(MetaPho.Image(filename))
        self.imgno = 0

        # The size of the image viewing area:
        self.imgwidth = 640
        self.imgheight = 600

        self.isearch = False

        self.win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.win.set_border_width(10)

        self.win.connect("delete_event", self.quit)
        self.win.connect("destroy", self.quit)

        main_hbox = gtk.HBox(spacing=8)

        self.viewer = gtkpho.ImageViewer()
        self.viewer.set_size_request(self.imgwidth, self.imgheight)
        main_hbox.pack_start(self.viewer)

        self.tagger = gtkpho.TagViewer(self.win)
        main_hbox.pack_start(self.tagger, expand=True)

        self.win.add(main_hbox)

        self.win.connect("key-press-event", self.key_press_event)
        self.win.show_all();

        self.read_all_tags()

    def quit(self, widget=None, data=None):
        # If focus is currently in a text entry, there may be changed
        # text that hasn't been updated yet in the tags list.
        # Call the tagger to warn about that.
        if type(self.win.get_focus()) is gtk.Entry:
            self.tagger.check_entry_tag(self.win.get_focus())

        print "==========="
        print self.tagger
        self.tagger.write_tag_file()

        # Can't call main_quit here: RuntimeError: called outside of a mainloop
        # Apparently this is what you're supposed to do instead:
        self.win.connect('event-after', gtk.main_quit)

    def read_all_tags(self):
        '''Read tags in all directories used by images in argv.
        '''
        dirlist = []
        for img in MetaPho.Image.g_image_list:
            dirname = os.path.dirname(img.filename)
            if dirname not in dirlist:
                dirlist.append(dirname)
                self.tagger.read_tags(dirname)
        self.tagger.display_tags()

    def first_image(self):
        self.imgno = -1
        self.next_image()

    def lastImage(self):
        self.imgno = len(MetaPho.Image.g_image_list)
        self.prev_image()

    def next_image(self):
        '''Advance to the next image, if possible.
           Tell the viewer to load and show the image.
        '''
        loaded = False

        # Save the tags of the current image, so we can copy them
        # into the next image if it doesn't have any yet.
        oldtags = None
        try:
            if self.imgno >= 0 and MetaPho.Image.g_image_list[self.imgno].tags:
                oldtags = MetaPho.Image.g_image_list[self.imgno].tags
        except:
            print "Couldn't load image #", self.imgno
            print "Tags:", MetaPho.Image.g_image_list[self.imgno].tags
            pass

        while self.imgno < len(MetaPho.Image.g_image_list)-1 and not loaded:
            self.imgno += 1
            img = MetaPho.Image.g_image_list[self.imgno]
            if img.displayed:
                loaded = self.viewer.load_image(img)
                if not loaded:
                    print "next_image: couldn't show", img.filename
                    img.displayed = False
                    # Should arguably delete it from the list
                    # so we don't continue to save tags for a
                    # file we can't load. But what if it's just
                    # temporarily unreadable and the user can fix it?
                    #del(MetaPho.Image.g_image_list[self.imgno])
                    # The loop is about to increment imgno, but we actually want
                    # it to stay the same since deleting the nonexistent image
                    # slid the next image into the current position;
                    # so decrement imgno now.
                    #self.imgno -= 1

        if loaded:
            # If we have an image, and it has no tags set yet,
            # clone the tags from the previous image:
            if oldtags and not MetaPho.Image.g_image_list[self.imgno].tags:
                MetaPho.Image.g_image_list[self.imgno].tags = oldtags[:]

            self.tagger.set_image(MetaPho.Image.g_image_list[self.imgno])

        else :           # couldn't load anything in the list
            print "No more images"
            dialog = gtk.MessageDialog(self.win,
                                       gtk.DIALOG_DESTROY_WITH_PARENT,
                                       gtk.MESSAGE_QUESTION,
                                       gtk.BUTTONS_OK_CANCEL,
                                       "No more images: quit?")
            dialog.set_default_response(gtk.RESPONSE_OK)
            response = dialog.run()
            dialog.destroy()
            if response == gtk.RESPONSE_OK:
                self.quit()

    def prev_image(self):
        loaded = False
        while self.imgno >= 1 and not loaded:
            self.imgno -= 1
            img = MetaPho.Image.g_image_list[self.imgno]
            if img.displayed:
                loaded = self.viewer.load_image(img)
                if not loaded:
                    print "prev_image: couldn't show", img.filename
                    img.displayed = False
                    # See comment in next_image
                    #del(MetaPho.Image.g_image_list[self.imgno])

        if loaded:
            self.tagger.set_image(MetaPho.Image.g_image_list[self.imgno])
        else :          # couldn't load anything in the list
            print "Can't go before first image"

    def delete_confirm(self):
        '''Ask the user whether to really delete an image.
           Return True for yes, False for no.
           Accept some keystrokes beyond the usual ones,
           e.g. d or ctrl-d confirms the delete.
        '''
        dialog = gtk.MessageDialog(self.win, 
                                   gtk.DIALOG_DESTROY_WITH_PARENT,
                                   gtk.MESSAGE_QUESTION, 
                                   #gtk.BUTTONS_YES_NO,
                                   gtk.BUTTONS_CANCEL,
                                   "Delete %s ?" % \
                                     MetaPho.Image.g_image_list[self.imgno])
        delete_btn = dialog.add_button("Delete", gtk.RESPONSE_YES)

        # Handle key events on the dialog,
        # to make it easier for the user to respond.
        # d (with or without ctrl) confirms the delete.
        # n or q cancels (in addition to the usual ESC).
        def delete_dialog_key_press(widget, event, dialog):
            if event.string in ('q', 'n'):
                dialog.emit("response", gtk.RESPONSE_NO)
                return True
            elif event.keyval == gtk.keysyms.d :  # d with or without ctrl
                dialog.emit("response", gtk.RESPONSE_YES)
                return True
            return False
        dialog.connect("key-press-event", delete_dialog_key_press, dialog)

        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_YES:
            return True
        return False

    def key_press_event(self, widget, event):
        '''Handle a key press event anywhere in the window'''
        if self.isearch:
            return self.isearch_key_press(widget, event)

        entry_focused = (type(self.win.get_focus()) is gtk.Entry)

        # ctrl-space goes to the next image, even if we're typing
        # in an entry. Nothing should be focused afterward.
        # or out of the entries if we're already typing in one.
        # Ctrl-space also goes to the next image.
        if (event.keyval == gtk.keysyms.space and \
            event.state & gtk.gdk.CONTROL_MASK):
            if entry_focused:
                self.tagger.focus_none()
            self.next_image()
            return True

        # ESC shifts focus out of the current entry (if any)
        # and makes sure nothing is focused.
        if event.keyval == gtk.keysyms.Escape:
            self.tagger.focus_none()
            return True

        # Return shifts focus to the next tag entry (never out of the entries).
        if event.keyval == gtk.keysyms.Return:
            self.tagger.focus_next_entry()
            return True

        if event.keyval == gtk.keysyms.Return and entry_focused:
            # Return when in an entry goes to the next entry
            self.tagger.focus_next_entry()
            return True

        # For any other keys, if focus is in a text entry, just let
        # the user type, and don't try to navigate.
        if entry_focused:
            #print "Focus is in an entry"
            return False

        # Ctrl-d means delete the current image (after confirmation)
        if event.keyval == gtk.keysyms.d and \
                event.state & gtk.gdk.CONTROL_MASK:
            if self.delete_confirm():
                MetaPho.Image.g_image_list[self.imgno].delete()
                self.imgno -= 1
                self.next_image()
            return True

        # Ctrl-U: clear tags, then leave focus in the first empty tag field.
        if event.keyval == gtk.keysyms.u and \
                event.state & gtk.gdk.CONTROL_MASK:
            self.tagger.clear_tags(MetaPho.Image.g_image_list[self.imgno])
            # Turns out auto-focusing the next entry is annoying,
            # so don't do it:
            # self.tagger.focus_next_entry()
            return True

        # Ctrl-Z is for when you accidentally hit a key that opens a
        # new tag, but the current tag is blank and you don't want
        # focus in that text field.
        # XXX

        # Ctrl-q quits.
        if event.keyval == gtk.keysyms.q and \
                event.state & gtk.gdk.CONTROL_MASK:
            self.quit()
            return True

        if event.string == " ":
            self.next_image()
            return True 
        if event.keyval == gtk.keysyms.BackSpace:
            self.prev_image()
            return True
        if event.keyval == gtk.keysyms.Home:
            self.first_image()
            return True
        if event.keyval == gtk.keysyms.End:
            self.lastImage()
            return True
        if event.keyval == gtk.keysyms.Right:
            self.viewer.rotate(270)
            return True
        if event.keyval == gtk.keysyms.Left:
            self.viewer.rotate(90)
            return True
        if event.keyval in [ gtk.keysyms.Up, gtk.keysyms.Down ]:
            self.viewer.rotate(180)
            return True

        # Alpha: it's a tag
        if event.string.isalpha():
            self.tagger.toggle_tag_by_letter(event.string,
                                    MetaPho.Image.g_image_list[self.imgno])
            return True

        # Digits: go to a specific tag category
        # (ignore digits too large to have a category).
        if event.string.isdigit():
            try:
                self.tagger.show_category_by_number(int(event.string))
            except IndexError:
                pass
            return True

        # + or -: go to next or previous tag
        if event.string == '+':
            self.tagger.next_category(1)
            return True
        if event.string == '-':
            self.tagger.next_category(-1)
            return True

        if event.string == '/':
            self.search_string = ''
            self.tagger.title.set_text("search: ")
            self.isearch = True
            return True

        # A key we didn't understand
        #print "Read key:", event.string, "keyval", event.keyval
        return False

    def isearch_key_press(self, widget, event):
        '''Handle key presses when we're in isearch mode,
           typing in a search pattern.
        '''

        # Return shifts out of isearch mode
        # but also accepts (shifts focus to) the first match.
        if event.keyval == gtk.keysyms.Return:
            self.tagger.focus_first_match(self.search_string)
            self.isearch = False
            self.tagger.title.set_text(os.path.basename(\
                    MetaPho.Image.g_image_list[self.imgno].filename))
            return True

        # ESC shifts out of isearch mode.
        if event.keyval == gtk.keysyms.Escape:
            self.isearch = False
            self.tagger.show_matches('')
            return True

        if event.string:
            self.search_string += event.string
            self.tagger.show_matches(self.search_string)
            return True

        return False

    def main(self):
        gtk.main()

def main():
    def Usage():
        print "Usage: %s file [file file ...]" \
            % os.path.basename(sys.argv[0])

    if len(sys.argv) <= 1:
        Usage()
        sys.exit(1)
    if sys.argv[1] == "-h" or sys.argv[1] == "--help":
        Usage()
        sys.exit(0)
    if sys.argv[1] == "-v" or sys.argv[1] == "--version":
        print  MetaPho.__version__
        sys.exit(0)

    metapho = MetaPhoWindow(sys.argv[1:])
    metapho.first_image()
    try:
        metapho.main()
    except KeyboardInterrupt:
        # Deliberately don't call self.quit() -- we may be using Ctrl-C
        # as a way to quit without updating anything.
        print '\n'
        # This doesn't do anything useful:
        # traceback.print_stack()
        sys.exit(1)

if __name__ == '__main__':
    main()
