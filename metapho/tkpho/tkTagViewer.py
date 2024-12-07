#!/usr/bin/env python

"""
GTK UI classes for metapho: an image tagger and viewer.
"""

# Copyright 2024 by Akkana Peck: share and enjoy under the GPL v2 or later.

import metapho
from metapho import MetaphoImage, g_image_list

from PhoWidget import PhoWidget, PhoImage, VERBOSE

import tkinter as tk
from tkinter import messagebox

import os, sys

from string import ascii_lowercase, ascii_uppercase
from functools import partial


root = tk.Tk()

class TkTagViewer(metapho.Tagger):

    PADDING = 1

    def __init__(self, img_list):
        for filename in img_list:
            g_image_list.append(PhoImage(filename))

        metapho.Tagger.__init__(self)

        self.num_rows = 26

        # default bg color, which we'll read once the window is up.
        # As I test it initially, it's #d9d9d9
        self.bg_color = "#bbbbbb"
        # bg color for tags that are set on this image
        self.active_bg_color = "#f7ffff"

        # Now one to hold the button box
        buttonbox = tk.Frame(root)
        # buttonbox.pack(side=tk.RIGHT)
        buttonbox.grid(row=0, column=1)

        # Configure columns to have equal width
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)

        # Image name at the top.
        self.img_name_label = tk.Label(buttonbox)
        self.img_name_label.grid(row=0, column=0, columnspan=4)

        # XXX Eventually, add category buttons here

        # The buttons, one for each lower and upper case letter
        self.buttons = [None] * 52
        self.entries = [None] * 52

        self.root_bindings = {
            '<Key-space>': self.next_image,
            '<Key-BackSpace>': self.prev_image,
            '<Control-Key-u>': self.clear_tags,
            '<Key-slash>': self.search
        }

        for row, letter in enumerate(ascii_lowercase):
            callback = partial(self.letter_button_press, letter)
            self.root_bindings[f'<Key-{letter}>'] = callback
            self.buttons[row] = tk.Button(buttonbox, text=letter,
                                          bg=self.bg_color,
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

            upletter = letter.upper()
            callback = partial(self.letter_button_press, upletter)
            self.buttons[row+self.num_rows] = tk.Button(buttonbox, text=letter.upper(),
                                             bg=self.bg_color,
                                             command=callback)
            self.buttons[row+self.num_rows].grid(row=row, column=2,
                                      padx=self.PADDING, pady=self.PADDING)
            self.entries[row+self.num_rows] = tk.Entry(buttonbox, width=29,
                                            bg=self.bg_color,
                                            name=f"entry{upletter}")
            self.entries[row+self.num_rows].grid(row=row, column=3,
                                      padx=self.PADDING, pady=self.PADDING)
            self.root_bindings[f'<Key-{upletter}>'] = callback

        # Tell the buttonbox to calculate its size, so we can choose
        # a comparable image viewer size
        buttonbox.update()
        # print("buttonbox size:",
        #       buttonbox.winfo_width(), buttonbox.winfo_height())

        # make a space to hold the image viewer
        viewer_frame = tk.Frame(root,
                                width=buttonbox.winfo_width(),
                                height=buttonbox.winfo_height())
        # viewer_frame.pack(side=tk.LEFT)
        viewer_frame.grid_propagate(False)
        viewer_frame.grid(row=0, column=0)

        # Image viewer on the left
        self.viewer_size = (int(buttonbox.winfo_width() * .9),
                            buttonbox.winfo_height())
        # print("viewer size is", self.viewer_size)
        # viewer_frame.resize(*self.viewer_`size)
        self.pho_widget = PhoWidget(viewer_frame, img_list=img_list,
                                    size=self.viewer_size)

        root.bind('<Key-Return>', self.new_tag)
        root.bind('<Key-Escape>', self.focus_none)

        self.global_key_bindings(True)

        # Exit on Ctrl-q
        root.bind('<Control-Key-q>', self.quit_handler)

        self.read_all_tags_for_images()

        self.pho_widget.next_image()

        # After next_image, now we should have all the tags.
        # So populate the tag entries.
        # print("initially, tag list:", self.tag_list)
        for i, tag in enumerate(self.tag_list):
            self.entries[i].delete(0, tk.END)
            self.entries[i].insert(0, tag)

        self.update_window_from_image()


    def global_key_bindings(self, enable):
        """TkInter doesn't have a way to override window-wide key bindings
           when focus goes to a widget that needs input, like an Entry.
           Therefore, when focus goes to an entry, call
           global_key_bindings(False) to temporarily disable
           all the other key bindings that might be typed in an entry.
           On focus out, call global_key_bindings(True) to restore them.
        """
        for key in self.root_bindings:
            if enable:
                root.bind(key, self.root_bindings[key])
            else:
                root.unbind(key, None)

    def next_image(self, event=None):
        try:
            self.pho_widget.next_image()
        except IndexError:
            if messagebox.askyesno("Last image", "Last image. Quit?"):
                self.quit_handler()

        self.update_window_from_image()

    def prev_image(self, event=None):
        self.pho_widget.prev_image()
        self.set_title()

    def set_title(self):
        img = g_image_list[self.pho_widget.imgno]
        root.title("%s (%d of %d)" % (
            os.path.basename(img.filename),
            self.pho_widget.imgno + 1,
            metapho.num_displayed_images()))

    @staticmethod
    def letter2index(letter):
        if letter.islower():
            return ord(letter) - ord('a')
        elif letter.isupper():
            return ord(letter) - ord('A') + self.num_rows
        return -1

    def on_focus_in(self, event):
        print("Focus in", event.widget)
        print("Focused widget is now", root.focus_get())
        if type(event.widget) is tk.Entry:
            self.global_key_bindings(False)

    def on_focus_out(self, event):
        if type(event.widget) is not tk.Entry:
            if VERBOSE or True:
                print("Focus out of something other than an entry")
                return

        print("Focus out", event.widget)
        # Find the tag number
        entry = event.widget
        print("entry name:", entry._name)
        entryno = self.letter2index(entry._name[-1])

        newstr = event.widget.get()
        # has the text been erased, or maybe never been there?
        if not newstr:
            return

        self.change_tag(entryno, newstr)

        # Enable global key bindings
        self.global_key_bindings(True)

    def focus_none(self, event):
        # Called on Escape.
        # Find the currently focused widget:
        w = root.focus_get()
        print("focus_none: previously focused widget:", w, type(w))
        if type(w) is tk.Entry:
            if not w.get():
                # Nothing was typed in, so un-highlight the row
                letter = w._name[-1]
                index = self.letter2index(letter)
                self.tag_enabled(index, False)

        # Set focus to none
        root.focus()

    def letter_button_press(self, letter, event=None):
        print("handler for:", letter)
        # Tk doesn't have actual toggle buttons; you have to handle
        # such things manually.
        buttonno = self.letter2index(letter)
        # print("button", buttonno, "is currently",
        #       self.buttons[buttonno].config())

    def search(self, event):
        print("Would Search!")

    def quit_handler(self, event=None):
        print("Bye")
        sys.exit(0)

    def new_tag(self, event=None):
        # Loop over entries to find the first blank one
        for i, entry in enumerate(self.entries):
            if not entry.get():
                self.tag_enabled(i, True)
                entry.focus_set()
                return
        # No blank entries
        print("All entries are full!")
        return

    def tag_enabled(self, entryno, enabled):
        if enabled:
            self.buttons[entryno].config(relief="sunken",
                                         bg=self.active_bg_color)
            self.entries[entryno].config(bg=self.active_bg_color)
        else:
            if not self.bg_color:
                self.bg_color = self.buttons[-1].cget('bg')
            self.buttons[entryno].config(relief="raised", bg=self.bg_color)
            self.entries[entryno].config(bg=self.bg_color)

    def clear_tags(self, event=None):
        """Clear all tags in the current window
        """
        # metapho.Tagger.clear_tags(self, img)
        for i, button in enumerate(self.buttons):
            self.tag_enabled(i, False)

    def update_window_from_image(self):
        img = g_image_list[self.pho_widget.imgno]
        if VERBOSE:
            print("Current image:", img)
            print("Current category:", self.current_category)
            print("All tags:", self.tag_list)

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

        if VERBOSE:
            print("tags:", img.tags)
        self.clear_tags()
        for tagno in img.tags:
            self.tag_enabled(tagno, True)

    def sync_to_image(self):
        """Update the current image to match any user changes to tags.
           Called on things like next_image and quit.
        """
        for entry in self.entries:
            XXXXXX


if __name__ == '__main__':
    tagger = TkTagViewer(img_list=sys.argv[1:])
    root.mainloop()

