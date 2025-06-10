#!/usr/bin/env python

"""
GTK UI classes for metapho: an image tagger and viewer.
This also contains main() for the Tk version of metapho.
"""

# Copyright 2024,2025 by Akkana Peck: share and enjoy under the GPL v2 or later.

import metapho
from metapho import MetaphoImage
from metapho import imagelist

from . import tk_pho_widget
from .tk_pho_image import tkPhoImage
from .tkpho import tkPhoWindow
from .tkdialogs import InfoDialog, message_dialog, askyesno_with_bindings, \
                       flash_message

import tkinter as tk
from tkinter import messagebox

import os, sys

from string import ascii_lowercase, ascii_uppercase
from functools import partial


class TkTagViewer(metapho.Tagger):
    """The main tk metapho window, working as a metapho Tagger"""

    PADDING = 1

    def __init__(self, img_list):

        metapho.Tagger.__init__(self)

        self.last_image_shown = None

        self.root = tk.Tk()

        self.num_rows = 26

        # A separate window to allow zooming or fullsize viewing
        self.pho_win = None

        # The Info dialog
        self.infobox = None

        # default bg color, which we'll read once the window is up.
        # As I test it initially, it's #d9d9d9
        self.bg_color = "#bbbbbb"
        # bg color for tags that are set on this image
        self.active_bg_color = "#f7ffff"
        self.highlight_bg_color = "#fff0f0"

        # Bindings that should always be active in the main window.
        self.global_bindings = {
            '<Control-Key-q>':     self.quit,

            '<Control-Key-space>': self.next_image,
            '<Key-Escape>':        self.focus_none,

            '<Control-Key-z>':     self.popup_pho_window,
            '<Key-Return>':        self.new_tag,
        }

        # Bindings for the popup pho window
        self.pho_bindings = {
            '<Control-Key-f>':     self.toggle_pho_fullsize,
            '<Control-Key-p>':     self.toggle_pho_fullscreen,
            '<Control-Key-q>':     self.hide_pho_window,
            '<Control-Key-w>':     self.hide_pho_window,
            '<Control-Key-z>':     self.hide_pho_window,
            '<Control-Key-space>': self.next_image,
        }

        # Bindings that will be disabled when focus is in a text field
        # Letter keys will be added to this
        self.win_bindings = {
            '<Key-space>':         self.next_image,
            '<Key-BackSpace>':     self.prev_image,
            '<Key-Home>':          partial(self.goto_image, 0),
            '<Key-End>':           partial(self.goto_image, -1),
            '<Control-Key-d>':     self.delete_image,
            '<Control-Key-u>':     self.clear_tag_buttons,
            '<Control-Key-i>':     self.show_info,
            '<Key-slash>':         self.focus_find,
        }

        # Bindings I want in all entries; I wish Tk had a
        # more configurable way of getting these
        self.entry_bindings = {
            '<Control-Key-u>':     self.entryerase,
        }

        # The root will be divided into two columns horizontally:
        # the image on the left, rightpane on the right.
        # rightpane holds the category selector and the buttonbox.
        # Above the buttonbox on the right goes the category selector,
        # which also holds the image name and search bar.

        rightpane = tk.Frame(self.root)
        rightpane.grid(row=0, column=1, padx=self.PADDING, pady=self.PADDING)

        # The category selector
        catsel = tk.Frame(rightpane)
        catsel.pack(side=tk.TOP)

        # Image name at the top of the catsel
        self.img_name_label = tk.Label(catsel)
        self.img_name_label.pack(side=tk.TOP)

        # In the next line below the image name, the various
        # category selection related widgets
        label = tk.Label(catsel, text="Category:")
        # label.grid(row=0, column=0)
        label.pack(side=tk.LEFT)

        # Option menu for changing category
        self.cat_menu_str = tk.StringVar(self.root)
        self.cat_option_menu = tk.OptionMenu(catsel, self.cat_menu_str, [])
        self.cat_option_menu.pack(side=tk.LEFT)

        b = tk.Button(catsel, text="New Category", command=self.new_category)
        # b.grid(row=0, column=3, columnspan=2,
        #        padx=self.PADDING, pady=self.PADDING)
        b.pack(side=tk.LEFT)

        findbox = tk.Frame(catsel)
        findbox.pack(side=tk.LEFT, expand=True)
        findlabel = tk.Label(findbox, text="Find:")
        findlabel.pack(side=tk.LEFT)
        # Apparently the only way to get notifications during typing
        # is to tie the entry to a string variable
        self.findstring = tk.StringVar()
        self.findentry = tk.Entry(findbox, textvariable=self.findstring)
        self.findentry.bind("<FocusIn>", self.on_focus_in)
        self.findentry.bind("<FocusOut>", self.on_find_focus_out)
        self.findentry.pack(side=tk.LEFT, expand=True)
        self.findstring.trace_add('write', self.update_find)
        for key in self.entry_bindings:
            self.findentry.bind(key, self.entry_bindings[key])

        # The buttonbox holds all the lettered buttons and their entries.
        buttonbox = tk.Frame(rightpane)
        buttonbox.pack(side=tk.BOTTOM)
        # buttonbox.grid(row=1, column=1)

        # Configure columns to have equal width
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        # The buttons, one for each lower and upper case letter
        self.buttons = [None] * 52
        self.entries = [None] * 52

        for row, letter in enumerate(ascii_lowercase):
            callback = partial(self.letter_button_press, letter)
            self.win_bindings[f'<Key-{letter}>'] = callback
            self.buttons[row] = tk.Button(buttonbox, text=letter,
                                          bg=self.bg_color,
                                          name=f'button{letter}',
                                          command=callback)
            self.buttons[row].grid(row=row+1, column=0,
                                   padx=self.PADDING, pady=self.PADDING)
            self.entries[row] = tk.Entry(buttonbox, width=29,
                                         bg=self.bg_color,
                                         name=f"entry{letter}")
            self.entries[row].grid(row=row+1, column=1,
                                   padx=self.PADDING, pady=self.PADDING)
            self.entries[row].bind("<FocusIn>", self.on_focus_in)
            self.entries[row].bind("<FocusOut>", self.on_focus_out)
            for key in self.entry_bindings:
                self.entries[row].bind(key, self.entry_bindings[key])

            upletter = letter.upper()
            callback = partial(self.letter_button_press, upletter)
            self.win_bindings[f'<Key-{upletter}>'] = callback
            self.buttons[row+self.num_rows] = tk.Button(buttonbox,
                                                        text=letter.upper(),
                                             bg=self.bg_color,
                                             command=callback)
            self.buttons[row+self.num_rows].grid(row=row+1, column=2,
                                      padx=self.PADDING, pady=self.PADDING)
            self.entries[row+self.num_rows] = tk.Entry(buttonbox, width=29,
                                            bg=self.bg_color,
                                            name=f"entry{upletter}")
            self.entries[row+self.num_rows].grid(row=row+1, column=3,
                                      padx=self.PADDING, pady=self.PADDING)
            self.entries[row+self.num_rows].bind('<Control-Key-u>', self.entryerase)
            self.entries[row+self.num_rows].bind("<FocusIn>", self.on_focus_in)
            self.entries[row+self.num_rows].bind("<FocusOut>", self.on_focus_out)

        # Tell the buttonbox to calculate its size, so we can choose
        # a comparable image viewer size
        buttonbox.update()

        # make a space to hold the image viewer
        viewer_frame = tk.Frame(self.root)
        # viewer_frame.pack(side=tk.LEFT)
        viewer_frame.grid_propagate(False)
        viewer_frame.grid(row=0, column=0)

        # Pho Image viewer on the left. Calculate a good width for it.
        # Height will be the same as the buttonbox.
        screenwidth = self.root.winfo_screenwidth()
        bboxwidth = buttonbox.winfo_width()
        viewerwidth = bboxwidth * 1.2
        EXTRA = 25
        if viewerwidth + bboxwidth > screenwidth + EXTRA:
            viewerwidth = (screenwidth - bboxwidth - EXTRA,
                           buttonbox.winfo_height())
        self.viewer_size = (int(viewerwidth), buttonbox.winfo_height())
        # viewer_frame.resize(*self.viewer_`size)

        self.pho_widget = tk_pho_widget.tkPhoWidget(viewer_frame,
                                                    img_list=img_list,
                                                    size=self.viewer_size)

        self.set_bindings(enable=True, widget=self.root, include_pho_win=False)

        self.read_all_tags_for_images()

        if not self.categories:
            print("No categories after reading Tags file")
            self.categories["Tags"] = list(self.tag_list)

        # Now we should have categories.
        # set current category to the first one
        self.current_category = next(iter(self.categories))

        # fill the category option menu
        self.cat_option_menu['menu'].delete(0, 'end')
        for cat in self.categories:
            self.cat_option_menu['menu'].add_command(label=cat,
                command=lambda c=cat: self.switch_category(c))
        self.cat_menu_str.set(self.current_category)

        try:
            self.pho_widget.next_image()
        except IndexError:
            # No viewable images will cause the pho_widget to raise
            # an IndexError when it tries repeatedly to do next_image().
            print("No viewable images!")
            # XXX For some reason, the window in this case resizes to
            # more than fill the screen, which is annoying.
            # But its winfo_width, height are more reasonable numbers,
            # they just aren't respected.
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if h > w:
                h = w
            self.root.geometry('%dx%d' % (w, h))
            message_dialog(title="No Images", message="No viewable images!",
                           yes_bindings=['<Key-space>'])
            sys.exit(1)

        # All the tags are read in and we're showing the first image.
        self.update_tag_entries()
        self.update_window_from_image(allow_category_change=True)

    def update_tag_entries(self):
        """Populate the entry widgets to show names of tags
           in the current category.
        """
        # First clear all entries
        for ent in self.entries:
            ent.delete(0, tk.END)

        omitted = []

        # Enumerate the tags in the first category in self.categories:
        if tk_pho_widget.VERBOSE:
            print("self.categories:", self.categories)
        for i, tagno in enumerate(self.categories[self.current_category]):
            tagname = self.tag_list[tagno]
            try:
                self.entries[i].insert(0, tagname)
            except IndexError:
                omitted.append(tagname)
        if omitted:
            flash_message("Too many tags, omitting %s" %
                          ', '.join(omitted), self.root)

    def switch_category(self, newcat):
        """Switch to a different current category, either because
           the user asked for it with the menu, or because the current
           image has no tags in the old current category but does
           in the new one.
        """
        self.update_image_from_window()
        if tk_pho_widget.VERBOSE:
            print("Change category to:", newcat)
        self.current_category = newcat
        self.cat_menu_str.set(newcat)
        self.update_tag_entries()
        self.update_window_from_image(allow_category_change=False)

    def new_category(self):
        newcatname = tk.simpledialog.askstring("New Category",
                                               "New category name:")
        if not newcatname:
            return
        if newcatname in self.categories:
            flash_message("You already have a %s category" % newcatname)
            return
        self.categories[newcatname] = []
        self.cat_option_menu['menu'].add_command(label=newcatname,
            command=lambda c=newcatname: self.switch_category(c))
        self.switch_category(newcatname)

    def set_bindings(self, enable, widget=None, include_pho_win=False):
        """TkInter doesn't have a way to override window-wide key bindings
           when focus goes to a widget that needs input, like an Entry.
           Therefore, when focus goes to an entry, call
           set_bindings(False) to temporarily disable
           all the other key bindings that might be typed in an entry.
           On focus out, call set_bindings(True) to restore them.

           This is also used to enable bindings in the child Pho window.
        """
        if not widget:
            widget = self.root

        if enable:
            for key in self.win_bindings:
                widget.bind(key, self.win_bindings[key])
            if include_pho_win and self.pho_win:
                for key in self.pho_bindings:
                    self.pho_win.root.bind(key, self.pho_bindings[key])
            else:
                for key in self.global_bindings:
                    widget.bind(key, self.global_bindings[key])
        else:
            for key in self.win_bindings:
                widget.unbind(key, None)

        # Also add ^Q and ^Z
        # self.pho_win.root.bind(key, self.global_bindings[key])

    def next_image(self, event=None):
        if tk_pho_widget.VERBOSE:
            print("\ntk_tag_viewer.next_image")
            # self.print_imagelist()
        self.last_image_shown = imagelist.current_image()
        self.focus_none()
        self.update_image_from_window()

        try:
            self.pho_widget.next_image()
        except IndexError:
            if askyesno_with_bindings("Last image",
                                      "Last image. Quit?",
                                      yes_bindings=['<Key-space>']):
                self.quit()
                # This sometimes fails to exit, and gives an error
                # when u_w_f_i calls set_title and there's no more titlebar.
                return

        self.update_window_from_image(allow_category_change=True)

    def prev_image(self, event=None):
        if tk_pho_widget.VERBOSE:
            print("\ntk_tag_viewer.prev_image")
            # self.print_imagelist()
        self.last_image_shown = imagelist.current_image()
        self.focus_none()
        self.update_image_from_window()

        self.pho_widget.prev_image()
        self.set_title()

        self.update_window_from_image(allow_category_change=True)

    def goto_image(self, imageno, event=None):
        self.last_image_shown = imagelist.current_image()
        self.focus_none()
        self.update_image_from_window()

        self.pho_widget.goto_imageno(imageno)
        self.set_title()

        self.update_window_from_image(allow_category_change=True)

    def set_title(self):
        img = imagelist.current_image()
        self.root.title("%s (%d of %d)" % (
            os.path.basename(img.filename),
            imagelist.current_imageno() + 1,
            metapho.num_displayed_images()))

    @staticmethod
    def letter2index(letter):
        if letter.islower():
            return ord(letter) - ord('a')
        elif letter.isupper():
            return ord(letter) - ord('A') + 26
        return -1

    def on_focus_in(self, event):
        if tk_pho_widget.VERBOSE:
            print("Focus in", event.widget)
        if type(event.widget) is tk.Entry:
            self.set_bindings(False)

    def on_focus_out(self, event):
        if type(event.widget) is not tk.Entry:
            if tk_pho_widget.VERBOSE:
                print("Focus out of something other than an entry")
            return

        # Find the tag number
        entry = event.widget
        entryno = self.letter2index(entry._name[-1])
        curcat = self.categories[self.current_category]
        newstr = entry.get().strip()

        if tk_pho_widget.VERBOSE:
            print("Focus out #%d %s, now '%s'" % (entryno, entry._name[-1],
                                                  newstr))

        # If nothing has changed, don't worry about it
        try:
            if newstr == self.tag_list[curcat[entryno]]:
                # Enable global key bindings
                self.set_bindings(True)
                return
        except IndexError:
            if tk_pho_widget.VERBOSE:
                print("Something changed or it's a new tag")
            pass

        # Most tag updating will happen in update_image_from_window().
        # The only tag-related actions that have to be done here,
        # since they might affect subsequent tags for this image, are:

        # 1. guard against an existing tag string being erased
        if not newstr:
            if tk_pho_widget.VERBOSE:
                print("Empty entry")
            if entryno < len(curcat):
                if curcat[entryno]:
                    if tk_pho_widget.VERBOSE:
                        print("entryno > len curcat, setting entry back to",
                              curcat[entryno])
                    entry.insert(0, curcat[entryno])
                else:
                    print("Category", curcat,
                          "seems to have a blank entry at", entryno,
                          ":", curcat)
            self.set_bindings(True)
            return

        # It has changed and is not the last entry, so
        # 2. guard against duplicate tags
        try:
            # Does the tag already exist?
            tagindex = self.tag_list.index(newstr)

        except ValueError:
            # It's a new tag, update_image_from_window() will deal with it
            if tk_pho_widget.VERBOSE:
                print("new tag, doing nothing for now")
            self.set_bindings(True)
            return

        # It's already in the tag list
        if tk_pho_widget.VERBOSE:
            print("Changing an entry %d to an already existing tag %s"
                  % (tagindex, newstr))

        # Is it already in the current category?
        try:
            catindex = curcat.index(tagindex)
            if tk_pho_widget.VERBOSE:
                print("index in current category:", catindex,
                      "(entryno is", entryno, ")")
            if catindex != entryno:
                if tk_pho_widget.VERBOSE:
                    print("Duplicate tag, previously at position",
                          catindex, "now duped at",
                          entryno, file=sys.stderr)

                # Enable and highlight the earlier instance of the tag --
                # but only if it's set for the current image.
                # It might not be set in the case where the user
                # entered the duplicate tag, then typed control-Return
                # to go to the next image, in which case on_focus_out
                # won't be called until the current image has already changed.
                if tagindex in imagelist.current_image().tags:
                    self.enable_entry(catindex, True)
                    self.entries[catindex].config(bg=self.highlight_bg_color)
                # Clear the entry where the duplicate was just typed
                if entryno >= len(curcat):
                    entry.delete(0, tk.END)
                    self.enable_entry(entryno, False)
                    self.focus_none()
                else:
                    try:
                        entry.insert(0, text=curcat[catindex])
                    except:
                        entry.insert(0, text='EEK ' + newstr)

        except ValueError:
            # It's in the tag list, but not in the current category.
            if tk_pho_widget.VERBOSE:
                print("It's in the tag list, but not n the current category.")
            # Is it new?
            if entryno >= len(curcat):
                print("appending")
                curcat.append(tagindex)
            else:
                # It's replacing an old tag?
                # I think this can happen if the user changes a tag
                # to a string that already exists as a tag in a
                # category other than the current category.
                print(newstr, "is already a tag but not in the",
                      self.current_category, "category. Replacing",
                      curcat[entryno])
                curcat[entryno] = tagindex

        # Enable global key bindings
        self.set_bindings(True)

        if tk_pho_widget.VERBOSE:
            print("End of on_focus_out:")
            self.print_imagelist()

    def focus_none(self, event=None):
        # Called on Escape, and from update_image_from_window.
        # Actually focuses the root, not nothing,
        # but the important thing is that it ensures that any
        # focused entry has been defocused and its contents handled.

        # Find the currently focused widget:
        w = self.root.focus_get()
        if type(w) is tk.Entry:
            if not w.get():
                # Nothing was typed in, so un-highlight the row.
                # Note: this means that erasing an existing tag is
                # equivalent to un-checking it; the assumption is
                # that if the user erased the tag, they probably
                # don't want it set for the current image, even
                # if the tag is kept for other images.
                letter = w._name[-1]
                index = self.letter2index(letter)
                self.enable_entry(index, False)

        # Set focus to the root window
        self.root.focus()
        # and ensure we have all the expected key bindings,
        # since we might have been in a text entry previously
        self.set_bindings(True, self.root)

    def letter_button_press(self, letter, event=None):
        # Tk doesn't have actual toggle buttons; you have to handle
        # such things manually.
        buttonno = self.letter2index(letter)
        # print("button", buttonno, "is currently",
        #       self.buttons[buttonno].config())

        # Is this tag blank, or is there a blank tag before this one?
        # Then refuse to enable it.
        if (not self.entries[buttonno].get().strip() or
            (buttonno > 0 and not self.entries[buttonno-1].get().strip())):
            if tk_pho_widget.VERBOSE:
                print("Refusing to go to tag", letter)
            return

        self.enable_entry(buttonno, not self.tag_button_set(buttonno))

        self.changed = True

    def entryerase(self, event):
        event.widget.delete(0, tk.END)

    def quit(self, event=None):
        print(len(imagelist.image_list()), "images")
        if self.tag_list:
            print("tags:", ", ".join(self.tag_list))
        if (len(self.categories) > 1 or
            (len(self.categories) == 1 and
             next(iter(self.categories)) != 'Tags')):
            print("categories:", ' '.join([key for key in self.categories]))

        # Write tags to disk, if they changed
        self.write_tag_file()

        self.root.destroy()
        # People say to quit by calling self.root.destroy(), but doing so leads to
        # _tkinter.TclError: can't invoke "wm" command:
        #     application has been destroyed
        # and it also doesn't exit right away, leading to problems
        # trying to update UI elements that have been destroed.
        # so call sys.exit to be sure:
        sys.exit(0)

    def new_tag(self, event=None):
        """The user hit Return to add a new tag.
           Find the first blank entry and focus it.
        """
        # Loop over entries to find the first blank one
        for i, entry in enumerate(self.entries):
            if not entry.get():
                self.enable_entry(i, True)
                entry.focus_set()
                self.changed = True
                return
        # W're full, no room for new entries
        flash_message(self.root, "All entries are full!")
        return

    def is_enabled(self, entryno):
        return self.buttons[entryno].cget('relief') == 'sunken'

    def enable_entry(self, entryno, enabled):
        """Make the given entry and button selected"""
        if enabled:    # turn on
            self.buttons[entryno].config(relief="sunken",
                                         bg=self.active_bg_color)
            self.entries[entryno].config(bg=self.active_bg_color)
        else:
            if not self.bg_color:
                self.bg_color = self.buttons[-1].cget('bg')
            self.buttons[entryno].config(relief="raised", bg=self.bg_color)
            self.entries[entryno].config(bg=self.bg_color)

    def tag_button_set(self, which):
        """which can be a button, an entry, or an integer index"""
        if type(which) is int:
            return self.buttons[which].cget('relief') == 'sunken'

        if type(which) is tk.Button:
            # print("button", which._name, which.cget('relief'))
            return which.cget('relief') == 'sunken'

        if type(which) is not tk.Entry:
            print("Error, tag_button_set called with a", type(which),
                  file=sys.stderr)
            return False

        index = self.letter2index(which._name[-1])
        return self.buttons[index].cget('relief') == 'sunken'

    def clear_tag_buttons(self, event=None):
        """Clear all tag buttons in the current window
        """
        # metapho.Tagger.clear_tag_buttons(self, img)
        for i, button in enumerate(self.buttons):
            self.enable_entry(i, False)

    def delete_image(self, event=None):
        ans = askyesno_with_bindings("Delete", "Really delete?",
                                     yes_bindings=['<Key-d>',
                                                   '<Control-Key-d>'])
        if ans:
            self.pho_widget.delete_current()

            # Was that the last viewable image?
            if (not imagelist.current_image() or
                type(imagelist.current_image()) is not tkPhoImage):
                message_dialog(title="No Images", message="No images left",
                               yes_bindings=['<Key-space>'])
                self.quit()

    def update_window_from_image(self, allow_category_change=False):
        """Set the buttons and entries to reflect the tags in the current
           image. If the current image has no tags yet, then leave the
           settings from the previous image.
        """
        img = imagelist.current_image()
        if tk_pho_widget.VERBOSE:
            print("update_window_from_image:")
            print("  img:", img, "tags:", img.tags)

        self.set_title()

        # Decide what category to show.
        # If the image has tags set in the current category,
        # or the image has no tags set in any category,
        # leave the current category unchanged.
        # Otherwise, switch to the first category where this image has tags.
        if tk_pho_widget.VERBOSE:
            print("Does it have tags in current category",
                  self.current_category, "?",
                  self.img_has_tags_in(img, self.current_category))
        if not self.img_has_tags_in(img, self.current_category):
            if not img.tags:
                if tk_pho_widget.VERBOSE:
                    print(img, "has no tags yet")
                if self.last_image_shown:
                    if tk_pho_widget.VERBOSE:
                        print("Copying tags from last image shown:",
                              self.last_image_shown.tags)
                    img.tags = list(self.last_image_shown.tags)
                elif tk_pho_widget.VERBOSE:
                    print("No self.last_image_shown")
            elif allow_category_change:
                for cat in self.categories:
                    if cat == self.current_category:
                        continue
                    if self.img_has_tags_in(img, cat):
                        # switch_category will call update_window_from_image
                        # so skip the next steps and trust that we'll
                        # come back here that way.
                        return self.switch_category(cat)
                    else:
                        print(img, "has no tags in", cat)
                else:  # triggered if all for iterations completed, no break
                    if tk_pho_widget.VERBOSE:
                        print(img, "has tags, but none in any category")
                    img.tags = self.last_image_shown.tags

        self.clear_tag_buttons()
        for i, b in enumerate(self.buttons):
            tagname = self.entries[i].get()
            tagno = self.tagname_to_tagno(tagname)
            self.enable_entry(i, tagno in img.tags)

        if self.pho_win:
            self.pho_win.goto_imageno(imagelist.current_imageno())

        # State may be normal, withdrawn or iconic
        if self.infobox and self.infobox.state() == 'normal':
            self.infobox.update_msg(self.pho_widget.current_image())

    def update_image_from_window(self):
        """Update tags in the current category according to
           the state of the buttons.
        """
        # Make sure the currently focused entry has been dealt with first:
        self.focus_none()

        img = imagelist.current_image()
        if tk_pho_widget.VERBOSE:
            print("update_image_from_window: img", img)

        # See what needs to be set/cleared in img.tags
        for i, b in enumerate(self.buttons):
            # The button indices is NOT the same as the index of the tag:
            # if there are multiple categories, we're showing fewer than the
            # total number of tags. So find the tag index:
            tagname = self.entries[i].get()

            if not tagname:
                # XXX should check whether the user has cleared this
                # tag name, and whether this index was previously set.
                # But for now, just bail if the entry is empty.
                continue

            # Did the tag name change?
            if tagname != self.categories[self.current_category]:
                if tk_pho_widget.VERBOSE:
                    print("Tag", self.categories[self.current_category],
                          "changing to", tagname)
                self.change_tag(i, tagname)

            # The button index *should* correspond to the index
            # of the tag in the current category. Check that:
            if i >= len(self.categories[self.current_category]):
                # Must be a new tag. Don't care if the button isn't down"
                if not self.tag_button_set(b):
                    continue
                if tk_pho_widget.VERBOSE:
                    print("Adding new tag", tagname)
                tagno = self.add_tag(tagname, img)
                continue

            # The current category is long enough to hold this index.
            # What tag does it point to?
            tagno = self.categories[self.current_category][i]
            if self.tag_list[tagno] != tagname:
                if tk_pho_widget.VERBOSE:
                    print("Changing tag", i,
                          self.tag_list[
                              self.categories[self.current_category][i]],
                          "->", tagname)

            # add or remove the tag, as appropriate
            if self.tag_button_set(b) and tagno not in img.tags:
                img.tags.append(tagno)
                if tk_pho_widget.VERBOSE:
                    print("Adding tag", i, tagno, "->", tagname)
            elif not self.tag_button_set(b) and tagno in img.tags:
                img.tags.remove(tagno)
                if tk_pho_widget.VERBOSE:
                    print("Removing tag", i, tagno, "->", tagname)

        if tk_pho_widget.VERBOSE:
            print("End of update_image_from_window:")
            print("   ", img, "tags are", img.tags)
            print()
            self.print_imagelist()
            print()

    def focus_find(self, event=None):
        """Open an entry where the user can type search strings,
           to search for tags.
        """
        self.findentry.focus()

        if self.findstring.get():
            self.update_find(None, None, None)

    def on_find_focus_out(self, event):
        # self.findentry.delete(0, tk.END)
        self.set_bindings(True)

    def update_find(self, var, index, mode):
        # I don't know what any of the arguments are, but it seems
        # they aren't useful for anything.
        findstr = self.findstring.get()
        # print("update_find:", findstr)
        if len(findstr) < 3:
            return
        for i, ent in enumerate(self.entries):
            if findstr in ent.get():
                ent.config(bg=self.highlight_bg_color)
            else:
                # Set the entry to the same background color as
                # its corresponding button
                ent.config(bg=self.buttons[i].cget('bg'))

    def print_imagelist(self):
        print("imagelist:")
        for img in imagelist.img_list:
            print("   ", img, "tags:",
                  '; '.join(["%d, %s" % (t, self.tag_list[t])
                             for t in img.tags ]))
        print("All tags:", self.tag_list)
        print("Current category:", self.categories[self.current_category])

    def popup_pho_window(self, event=None):
        if not self.pho_win:
            self.pho_win = tkPhoWindow(parent=self.root,
                                       fixed_size=None, fullscreen=False)
            self.pho_win.root.protocol("WM_DELETE_WINDOW",
                                       lambda: self.pho_win.root.withdraw())
        else:
            self.pho_win.root.deiconify()

        # self.pho_win.pho_widget.goto_imageno(g_cur_imgno)
        self.pho_win.pho_widget.show_image()

        self.set_bindings(True, widget=self.pho_win.root, include_pho_win=True)

    def hide_pho_window(self, event=None):
        self.pho_win.root.iconify()

    # On Ctrl-F, toggle the pho win between zoom-to-fullsize and fit-on-screen
    def toggle_pho_fullsize(self, event=None):
        # Try to verify that this is in the pho_win and it's active,
        # though hopefully this won't be bound in any other windows.
        if not self.pho_win:
            return
        if self.pho_win.root.state() != 'normal':
            print("Got a ctrl-p for a pho_win with state",
                  self.pho_win.root.state(), file=sys.stderr)
        if event and event.widget:
            if not event.widget.title().startswith("Pho"):
                print("Eek, Ctrl-F toggle_pho_fullsize in the wrong window,",
                      event.widget, event.widget.title(), file=sys.stderr)
                return

        self.pho_win.fullsize_handler()

    # On Ctrl-p key, toggle between fullscreen mode and not for the pho_window
    def toggle_pho_fullscreen(self, event=None):
        # Try to verify that this is in the pho_win and it's active,
        # though hopefully this won't be bound in any other windows.
        if not self.pho_win:
            return
        if self.pho_win.root.state() != 'normal':
            print("Got a ctrl-p for a pho_win with state",
                  self.pho_win.root.state(), file=sys.stderr)
        if event and event.widget:
            if not event.widget.title().startswith("Pho"):
                print("Eek, Ctrl-p toggle_pho_fullscreen in the wrong window,",
                      event.widget, event.widget.title(), file=sys.stderr)
                return

        self.pho_win.go_fullscreen(None)

    def show_info(self, event=None):
        """Pop up the infobox (creating it if needed) and update its contents
        """
        # If this seems like it duplicates code in tkpho.py,
        # that's because it does. Both apps, pho and metapho,
        # need to be able to manage info window.
        if self.infobox:
            self.infobox.deiconify()
        else:
            self.infobox = InfoDialog()

        self.infobox.update_msg(self.pho_widget.current_image())


def main():
    def Usage():
        print("Usage: %s [-v] image1.jpg image2.jpg ..."
              % os.path.basename(sys.argv[0]))
        sys.exit(1)

    args = sys.argv[1:]
    if args[0] == '-v':
        tk_pho_widget.VERBOSE = True
        args = args[1:]
    elif args[0] == '-h' or args[0] == '--help':
        Usage()
    elif args[0][0] == '-':
        Usage()

    tagger = TkTagViewer(img_list=args)

    try:
        tagger.root.mainloop()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        sys.exit(0)


if __name__ == '__main__':
    main()

