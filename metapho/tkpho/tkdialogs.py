#!/usr/bin/env python3

import tkinter as tk

# This doesn't work:
# from tkinter.messagebox import *
# though this does:
#from tkinter.messagebox import _show
# so instead we'll have to preface everything with mb.
# from tkinter import messagebox as mb    # doesn't automatically import

from tkinter.simpledialog import Dialog

#
# InfoDialog window
#

class InfoDialog(tk.Toplevel):
    """The InfoDialog is non-modal, and shows details about the
       current image, like EXIF. It should be possible to keep it up
       and have it change as the image changes.
    """
    def __init__(self, *args, **kwargs):
        tk.Toplevel.__init__(self, *args, **kwargs)
        self.__text = tk.StringVar()
        self.__text.set("Info Dialog")
        tk.Label(self, textvariable = self.__text) \
          .grid(row=0, column=0, columnspan=3, sticky=tk.NW+tk.SE)
        tk.Button(self, text="OK", command=self.destroy_func) \
          .grid(row=1, column=1, sticky=tk.NW+tk.SE)
        # self.bind_all("<KeyDestroy>", self.destroy_func)
        self.grid()
        # self.focus_set()
        self.bind("<Return>", self.popdown)
        self.bind("<Escape>", self.popdown)

    def set_text(self, text):
        self.__text.set(text)
        # self.focus_set()

    def popdown(self, event=None):
        self.withdraw()       # or iconify()

    def destroy_func(self, event=None):
        # event=None necessary as we also use button binding.
        self.popdown()


#
# Custom messagebox, since messagebox doesn't allow for any additions
#

class CustomDialog(Dialog):
    def __init__(self, title, message, icon, master=None, yes_bindings=[]):
        """
        icon can be "information", "warning", "error" or "question"
        """
        self.message = message
        self.icon = icon
        self.yes_bindings = yes_bindings
        super().__init__(master, title)

    def body(self, parent):
        # get the system icon image
        self.photo = tk.PhotoImage(master=parent)
        self.tk.call(self.photo, "copy", f"::tk::icons::{self.icon}")
        # create label with the icon image and message
        tk.Label(parent, text=self.message,
                 compound="left").pack(padx=50, pady=20)

    def buttonbox(self):
        box = tk.Frame(self)
        state = tk.NORMAL
        self.ok_btn = tk.Button(box, text="OK", width=20, command=self.ok,
                                default=tk.ACTIVE, state=state)
        self.ok_btn.pack(side=tk.LEFT, padx=5, pady=5)
        self.cancel_btn = tk.Button(box, text="Cancel", width=20,
                                    command=self.cancel, state=state)
        self.cancel_btn.pack(side=tk.LEFT, padx=5, pady=5)
        box.pack()
        self._bindings()

    def _bindings(self):
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        for key in self.yes_bindings:
            self.bind(key, self.ok)

    def apply(self, event=None):
        self.result = True

    def cancel(self, event=None):
        super().cancel(event)


def askyesno_with_bindings(title=None, message=None, yes_bindings=[]):
    dlg = CustomDialog(title=title, message=message, icon="question",
                       yes_bindings=yes_bindings)
    return dlg.result


if __name__ == '__main__':
    infobox = None
    def popup_dialogs():
        infobox = InfoDialog()
        infobox.set_text("Show this message\nwith lots\nof extra lines, some of which are long\nand hopefully won't wrap")

        ans = askyesno_with_bindings("Custom yesno",
                                     "Do you want  to quit now?",
                                     yes_bindings=['<Key-q>', '<Key-d>'])
        print("answer:", ans)
        if ans:
            root.quit()

    root = tk.Tk()
    tk.Button(root, text="push me", command=popup_dialogs).pack()

    root.mainloop()

