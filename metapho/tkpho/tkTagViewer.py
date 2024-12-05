#!/usr/bin/env python

"""
GTK UI classes for metapho: an image tagger and viewer.
"""

# Copyright 2024 by Akkana Peck: share and enjoy under the GPL v2 or later.

import metapho

from PhoWidget import PhoWidget

import tkinter as tk
from tkinter import messagebox

import os, sys

from string import ascii_lowercase
from functools import partial


root = tk.Tk()

class TkTagViewer(metapho.Tagger):

    PADDING = 1

    def __init__(self, img_list):

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

        for row, letter in enumerate(ascii_lowercase):
            # Button doesn't pass an event with its callback,
            # so have to use a partial here.
            # Lambda doesn't work, because lambdas inside a loop
            # end up all using the last value of the loop, i.e. 'z'.
            # callback = lambda: self.letter_button_press(letter)
            callback = partial(self.letter_button_press, letter)
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
            root.bind(f'<Key-{letter}>', callback)

            callback = partial(self.letter_button_press, letter.upper())
            upletter = letter.upper()
            self.buttons[row+26] = tk.Button(buttonbox, text=letter.upper(),
                                             bg=self.bg_color,
                                             command=callback)
            self.buttons[row+26].grid(row=row, column=2,
                                      padx=self.PADDING, pady=self.PADDING)
            self.entries[row+26] = tk.Entry(buttonbox, width=29,
                                            bg=self.bg_color,
                                            name=f"entry{upletter}")
            self.entries[row+26].grid(row=row, column=3,
                                      padx=self.PADDING, pady=self.PADDING)
            root.bind(f'<Key-{upletter}>', callback)

        # Tell the buttonbox to calculate its size, so we can choose
        # a comparable image viewer size
        buttonbox.update()
        print("buttonbox size:",
              buttonbox.winfo_width(), buttonbox.winfo_height())

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
        print("viewer size is", self.viewer_size)
        # viewer_frame.resize(*self.viewer_`size)
        self.pho_widget = PhoWidget(viewer_frame, img_list=img_list,
                                    size=self.viewer_size)

        root.bind('<Key-space>', self.next_image_handler)
        root.bind('<Key-Return>', self.new_tag)
        root.bind('<Key-Escape>', self.focus_none)
        root.bind('<Control-Key-u>', self.clear_tags)

        root.bind('<Key-slash>', self.search)

        # Exit on Ctrl-q
        root.bind('<Control-Key-q>', self.quit_handler)

        self.pho_widget.next_image()

    def next_image_handler(self, event):
        try:
            self.pho_widget.next_image()
        except IndexError:
            if messagebox.askyesno("Last image", "Last image. Quit?"):
                self.quit_handler()

    def prev_image_handler(self, event):
        self.pho_widget.prev_image()

    def on_focus_in(self, event):
        print("Focus in", event.widget)
        print("Focused widget is now", root.focus_get())

    def on_focus_out(self, event):
        print("Focus out", event.widget)

    @staticmethod
    def letter2index(letter):
        if letter.islower():
            return ord(letter) - ord('a')
        elif letter.isupper():
            return ord(letter) - ord('A') + 26
        return -1

    def focus_none(self, event):
        # Called on Escape.
        # Find the currently focused widget:
        w = root.focus_get()
        print("focused widget:", w, type(w))
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
        print("button", buttonno, "is currently", self.buttons[buttonno].config())

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

    def clear_tags(self, event):
        """Clear all tags in the current window
        """
        metapho.Tagger.clear_tags(self, img)
        for i, button in enumerate(self.buttons):
            self.tag_enabled(i, False)


if __name__ == '__main__':
    tagger = TkTagViewer(img_list=sys.argv[1:])
    root.mainloop()

