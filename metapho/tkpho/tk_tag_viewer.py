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

        # Now one to hold the button box
        buttonbox = tk.Frame(self.root)
        # buttonbox.pack(side=tk.RIGHT)
        buttonbox.grid(row=0, column=1)

        # Configure columns to have equal width
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        # Image name at the top.
        self.img_name_label = tk.Label(buttonbox)
        self.img_name_label.grid(row=0, column=0, columnspan=4)

        # Add the category selector
        catsel = tk.Frame(buttonbox)
        catsel.grid(row=0, column=0, columnspan=2,
                   padx=self.PADDING, pady=self.PADDING)
        label = tk.Label(catsel, text="Category:")
        label.grid(row=0, column=0)
        self.cat_menu_btn = tk.Menubutton(catsel, text="Category menu",
                                          relief="raised")
        self.cat_menu_btn.grid(row=0, column=1)
        self.cat_menu_btn.menu = tk.Menu(self.cat_menu_btn, tearoff=0)
        # Is the next line really needed?
        self.cat_menu_btn["menu"] = self.cat_menu_btn.menu

        b = tk.Button(buttonbox, text="New Category", command=self.new_category)
        b.grid(row=0, column=3, columnspan=2,
               padx=self.PADDING, pady=self.PADDING)

        # The buttons, one for each lower and upper case letter
        self.buttons = [None] * 52
        self.entries = [None] * 52

        # Bindings that should always be active.
        self.global_bindings = {
            '<Control-Key-q>':     self.quit,

            '<Control-Key-space>': self.next_image,
            '<Key-Escape>':        self.focus_none,

            '<Control-Key-z>':     self.popup_pho_window,
            '<Key-Return>':        self.new_tag,
        }

        # Bindings that will be disabled when focus is in a text field
        # Letter keys will be added to this
        self.win_bindings = {
            '<Key-space>':         self.next_image,
            '<Key-BackSpace>':     self.prev_image,
            '<Key-slash>':         self.search,
            '<Key-Home>':          partial(self.goto_image, 0),
            '<Key-End>':           partial(self.goto_image, -1),
            '<Control-Key-d>':     self.delete_image,
            '<Control-Key-u>':     self.clear_tag_buttons,
            '<Control-Key-i>':     self.show_info,
        }

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
            self.entries[row].bind('<Control-Key-u>', self.entryerase)

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

        self.set_bindings(True, self.root)

        self.read_all_tags_for_images()

        # Now we should have categories and can populate the category menu
        if self.categories:
            for cat in self.categories:
                self.cat_menu_btn.menu.add_command(
                    label=cat,
                    command=lambda newcat=cat: self.switch_category(newcat))
        else:
            print("No categories after reading Tags file")
            self.categories["Tags"] = list(self.tag_list)
            self.cat_menu_btn.menu.add_command(
                label="Tags",
                command=lambda: self.switch_category("Tags"))

        # set current category to the first one
        self.current_category = next(iter(self.categories))
        self.cat_menu_btn.configure(text=self.current_category)

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
        print("Change category to:", newcat)
        self.current_category = newcat
        self.cat_menu_btn.configure(text=newcat)
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
        self.cat_menu_btn.menu.add_command(
                    label=newcatname,
                    command=lambda: self.switch_category(newcatname))
#                    command=lambda cat=newcatname: self.switch_category(cat))

    def set_bindings(self, enable, widget=None):
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
            for key in self.global_bindings:
                widget.bind(key, self.global_bindings[key])
            for key in self.win_bindings:
                widget.bind(key, self.win_bindings[key])
        else:
            for key in self.win_bindings:
                widget.unbind(key, None)

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

        if tk_pho_widget.VERBOSE:
            print("Focus out", event.widget)
        # Find the tag number
        entry = event.widget
        entryno = self.letter2index(entry._name[-1])

        newstr = event.widget.get()
        # has the text been erased, or maybe never been there?
        if not newstr:
            return

        self.change_tag(entryno, newstr)

        # Enable global key bindings
        self.set_bindings(True)

        if tk_pho_widget.VERBOSE:
            print("After focus_out:")
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
                # Nothing was typed in, so un-highlight the row
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

        # Is there a blank tag before this one? Then refuse to enable it.
        if buttonno > 0 and not self.entries[buttonno-1].get().strip():
            if tk_pho_widget.VERBOSE:
                print("Refusing to go to tag", letter)
            return

        self.enable_entry(buttonno, not self.tag_button_set(buttonno))

        self.changed = True

    def entryerase(self, event):
        event.widget.delete(0, tk.END)

    def search(self, event):
        print("Would Search!")

    def quit(self, event=None):
        if self.tag_list:
            print("tags:", self.tag_list)
        if self.categories:
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

            # See if the name is the same as an existing tag
            # existing_tagno = self.tagname_to_tagno(tagname)
            # if tk_pho_widget.VERBOSE:
            #     print(tagname, "already exists")
            # XXX Check whether it's in this category, or in another
            # and needs to be added to this one.

            # The button index *should* correspond to the index
            # of the tag in the current category. Check that:
            if i >= len(self.categories[self.current_category]):
                # Must be a new tag. Don't care if the button isn't down"
                if not self.tag_button_set(b):
                    continue
                if tk_pho_widget.VERBOSE:
                    print("Adding new tag", tagname)
                tagno = self.add_tag(tagname, img)
                if not tagno:
                    print("EEK, couldn't add tag", tagname)
                    continue
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

        self.set_bindings(True, widget=self.pho_win.root)

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
    args = sys.argv[1:]
    if args[0] == '-v':
        tk_pho_widget.VERBOSE = True
        args = args[1:]

    tagger = TkTagViewer(img_list=args)

    try:
        tagger.root.mainloop()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        sys.exit(0)


if __name__ == '__main__':
    main()

