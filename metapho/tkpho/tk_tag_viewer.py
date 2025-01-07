#!/usr/bin/env python

"""
GTK UI classes for metapho: an image tagger and viewer.
This also contains main() for the Tk version of metapho.
"""

# Copyright 2024,2025 by Akkana Peck: share and enjoy under the GPL v2 or later.

import metapho
from metapho import MetaphoImage
from metapho import imagelist

from .tk_pho_widget import tkPhoWidget, VERBOSE
from .tkpho import tkPhoWindow

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

        self.root = tk.Tk()

        self.num_rows = 26

        # A separate window to allow zooming or fullsize viewing
        self.pho_win = None

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

        # XXX Eventually, add category buttons here

        # The buttons, one for each lower and upper case letter
        self.buttons = [None] * 52
        self.entries = [None] * 52

        # Bindings that we want always to be active.
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
            '<Control-Key-u>':     self.clear_tags,
        }

        for row, letter in enumerate(ascii_lowercase):
            callback = partial(self.letter_button_press, letter)
            self.win_bindings[f'<Key-{letter}>'] = callback
            self.buttons[row] = tk.Button(buttonbox, text=letter,
                                          bg=self.bg_color,
                                          name=f'button{letter}',
                                          command=callback)
            self.buttons[row].grid(row=row, column=0,
                                   padx=self.PADDING, pady=self.PADDING)
            self.entries[row] = tk.Entry(buttonbox, width=29,
                                         bg=self.bg_color,
                                         name=f"entry{letter}")
            self.entries[row].grid(row=row, column=1,
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
            self.buttons[row+self.num_rows].grid(row=row, column=2,
                                      padx=self.PADDING, pady=self.PADDING)
            self.entries[row+self.num_rows] = tk.Entry(buttonbox, width=29,
                                            bg=self.bg_color,
                                            name=f"entry{upletter}")
            self.entries[row+self.num_rows].grid(row=row, column=3,
                                      padx=self.PADDING, pady=self.PADDING)
            self.entries[row+self.num_rows].bind('<Control-Key-u>', self.entryerase)
            self.entries[row+self.num_rows].bind("<FocusIn>", self.on_focus_in)
            self.entries[row+self.num_rows].bind("<FocusOut>", self.on_focus_out)

        # Tell the buttonbox to calculate its size, so we can choose
        # a comparable image viewer size
        buttonbox.update()
        # print("buttonbox size:",
        #       buttonbox.winfo_width(), buttonbox.winfo_height())

        # make a space to hold the image viewer
        viewer_frame = tk.Frame(self.root,
                                width=buttonbox.winfo_width(),
                                height=buttonbox.winfo_height())
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

        self.pho_widget = tkPhoWidget(viewer_frame, img_list=img_list,
                                      size=self.viewer_size)

        self.set_bindings(True, self.root)

        self.read_all_tags_for_images()

        self.pho_widget.next_image()

        # After next_image, now we should have all the tags.
        # So populate the tag entries.
        for i, tag in enumerate(self.tag_list):
            self.entries[i].delete(0, tk.END)
            self.entries[i].insert(0, tag)

        self.update_window_from_image()


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
        self.focus_none()
        self.update_image_from_window()

        try:
            self.pho_widget.next_image()
        except IndexError:
            if messagebox.askyesno("Last image", "Last image. Quit?"):
                self.quit()

        self.update_window_from_image()

    def prev_image(self, event=None):
        self.focus_none()
        self.update_image_from_window()

        self.pho_widget.prev_image()
        self.set_title()

        self.update_window_from_image()

    def goto_image(self, imageno, event=None):
        self.focus_none()
        self.update_image_from_window()

        self.pho_widget.goto_imageno(imageno)
        self.set_title()

        self.update_window_from_image()

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
        if VERBOSE:
            print("Focus in", event.widget)
        if type(event.widget) is tk.Entry:
            self.set_bindings(False)

    def on_focus_out(self, event):
        if type(event.widget) is not tk.Entry:
            if VERBOSE:
                print("Focus out of something other than an entry")
                return

        if VERBOSE:
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

    def focus_none(self, event=None):
        # Called on Escape.
        # Actually focuses the root, not nothing.

        # Find the currently focused widget:
        w = self.root.focus_get()
        if type(w) is tk.Entry:
            if not w.get():
                # Nothing was typed in, so un-highlight the row
                letter = w._name[-1]
                index = self.letter2index(letter)
                self.enable_tag(index, False)

        # Set focus to none
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
            if VERBOSE:
                print("Refusing to go to tag", letter)
            return

        self.enable_tag(buttonno, not self.tag_enabled(buttonno))

        self.changed = True

    def entryerase(self, event):
        event.widget.delete(0, tk.END)

    def search(self, event):
        print("Would Search!")

    def quit(self, event=None):
        # Write tags to disk, if they changed
        self.write_tag_file()
        self.root.destroy()
        # People say to quit by calling self.root.destroy(), but doing so leads to
        # _tkinter.TclError: can't invoke "wm" command:
        #     application has been destroyed
        # so call sys.exit instead:
        sys.exit(0)

    def new_tag(self, event=None):
        # Loop over entries to find the first blank one
        for i, entry in enumerate(self.entries):
            if not entry.get():
                self.enable_tag(i, True)
                entry.focus_set()
                self.changed = True
                return
        # W're full, no room for new entries
        print("All entries are full!", file=sys.stderr)
        return

    def enable_tag(self, entryno, enabled):
        if enabled:    # turn on
            self.buttons[entryno].config(relief="sunken",
                                         bg=self.active_bg_color)
            self.entries[entryno].config(bg=self.active_bg_color)
        else:
            if not self.bg_color:
                self.bg_color = self.buttons[-1].cget('bg')
            self.buttons[entryno].config(relief="raised", bg=self.bg_color)
            self.entries[entryno].config(bg=self.bg_color)

    def tag_enabled(self, which):
        """which can be a button, an entry, or an integer index"""
        if type(which) is int:
            return self.buttons[which].cget('relief') == 'sunken'

        if type(which) is tk.Button:
            # print("button", which._name, which.cget('relief'))
            return which.cget('relief') == 'sunken'

        if type(which) is not tk.Entry:
            print("Error, tag_enabled called with a", type(which),
                  file=sys.stderr)
            return False

        index = self.letter2index(which._name[-1])
        return self.buttons[index].cget('relief') == 'sunken'

    def clear_tags(self, event=None):
        """Clear all tags in the current window
        """
        # metapho.Tagger.clear_tags(self, img)
        for i, button in enumerate(self.buttons):
            self.enable_tag(i, False)

    def delete_image(self, event=None):
        ans = messagebox.askyesno("Delete", "Really delete?")

        if ans:
            self.pho_widget.delete_current()

    def update_window_from_image(self):
        """Set the buttons and entries to reflect the tags in the current
           image. If the current image has no tags yet, then leave the
           settings from the previous image.
        """
        img = imagelist.current_image()
        # if VERBOSE:
        #     print("Current image:", img)
        #     print("Current category:", self.current_category)
        #     print("All tags:", self.tag_list)

        self.set_title()

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

        # categories aren't implemented yet
        # self.catviewer.set_active(self.current_category)
        # self.highlight_categories()
        # self.display_tags_for_category(self.current_category)

        if img.tags:
            self.clear_tags()
            for tagno in img.tags:
                self.enable_tag(tagno, True)

        if self.pho_win:
            self.pho_win.goto_imageno(imagelist.current_imageno())

    def update_image_from_window(self):
        img = imagelist.current_image()
        img.tags = [ i for i, b in enumerate(self.buttons)
                     if self.tag_enabled(b) ]

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


def main():
    tagger = TkTagViewer(img_list=sys.argv[1:])
    try:
        tagger.root.mainloop()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        sys.exit(0)


if __name__ == '__main__':
    main()

