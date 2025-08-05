#!/usr/bin/env python3

import tkinter as tk
import tkinter.scrolledtext as scrolledtext

# This doesn't work:
# from tkinter.messagebox import *
# though this does:
#from tkinter.messagebox import _show
# so instead we'll have to preface everything with mb.
# from tkinter import messagebox as mb    # doesn't automatically import

from tkinter.simpledialog import Dialog

import sys


WANTED_EXIF_TAGS = [
    'Make', 'Model', 'Software',
    'LensMake', 'LensModel',
    'Orientation',
    'DateTime',
    'FocalLength', 'FNumber', 'ExposureTime',
    'ShutterSpeedValue', 'ApertureValue', 'BrightnessValue',

    'GPS coordinates',    # As decoded by TkPhoImage

    'WhiteBalance', 'ExposureBiasValue', 'MaxApertureValue',
    'FocalLengthIn35mmFilm',
    'SubjectDistance',
    'MeteringMode', 'Flash',
    'DigitalZoomRatio',
    # 'ColorSpace',
    # 'SceneCaptureType', 'SensingMethod', 'ExposureProgram', 'ExposureMode',
    # 'Contrast', 'Saturation', 'Sharpness', 'SubjectDistanceRange',
    # 'CompositeImage'
]


#
# InfoDialog window
#
class InfoDialog(tk.Toplevel):
    """The InfoDialog is non-modal, and shows details about the
       current image, like EXIF. It should be possible to keep it up
       and have it change as the image changes.
       Typically it will be used as a singleton.
    """
    def __init__(self, *args, **kwargs):
        tk.Toplevel.__init__(self, *args, **kwargs)

        self.textarea = scrolledtext.ScrolledText(self, padx=7, pady=7)
        self.textarea.grid(row=0, column=0, columnspan=3, sticky=tk.NW+tk.SE)

        # textarea fonts
        self.textarea.tag_configure('normal', font=('sans', 11))
        self.textarea.tag_configure('bold', font=('sans', 11, 'bold'))
        self.textarea.tag_configure('title', font=('Sans', 15, 'bold'))

        tk.Button(self, text="OK", command=self.destroy_func) \
          .grid(row=1, column=1, sticky=tk.NW+tk.SE)
        # self.bind_all("<KeyDestroy>", self.destroy_func)

        self.grid()
        # On resizing, fill empty space with the textarea
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # self.focus_set()
        self.bind("<Return>", self.popdown)
        self.bind("<Escape>", self.popdown)
        # Iconify on the titlebar 'x' as well
        self.protocol('WM_DELETE_WINDOW', self.popdown)

    def update_msg(self, cur_im, tagger=None):
        """Update the message shown in the info dialog.
           Needs the Tagger in order to map tag numbers to strings,
           else it will just show tag numbers.
        """
        self.title(cur_im.relpath)

        messagelist = []

        messagelist.append((cur_im.relpath + '\n', 'title'))
        if cur_im.orig_img:
            messagelist.append(('Actual size: ', 'bold',
                               str(cur_im.orig_img.size), 'normal'))
        if cur_im.display_img:
            messagelist.append(('Displayed size: ', 'bold',
                                str(cur_im.display_img.size), 'normal'))
        messagelist.append(('Rotation: ', 'bold',
                            str(cur_im.rot), 'normal'))
        messagelist.append(('EXIF Rotation: ', 'bold',
                            cur_im.exif_rotation, 'normal'))

        # What tags are set?
        if tagger:
            messagelist.append(('', 'normal'))    # paragraph break
            messagelist.append(('Tags: ', 'title'))
            if cur_im.tags:
                tagdict = tagger.tagdict_for_img(cur_im)
                for cat in tagdict:
                    if cat != 'Tags':
                        tagmessages = ['Category ' + cat + ': ', 'bold']
                    else:
                        tagmessages = []
                    tagmessages.append(', '.join([
                        tagger.tag_list[tagno] for tagno in tagdict[cat] ]))
                    tagmessages.append('normal')
                    messagelist.append(tagmessages)
            else:
                tagmessages = ('None', 'normal')
        else:
            messagelist += ( 'Tags: ', 'bold',
                            ', '.join([ str(t) for t in cur_im.tags ]),
                            'normal' )

        exif = cur_im.get_exif()
        if exif:
            messagelist.append(('', 'normal'))    # paragraph break
            messagelist.append(('EXIF: ', 'title'))
            for key in WANTED_EXIF_TAGS:
                if key in exif:
                    messagelist.append((key + ': ', 'bold', exif[key], 'normal'))

        # The message is now ready to show
        self.set_text(messagelist)

    @staticmethod
    def string_size(text):
        w = 0
        h = 0
        for line in text.splitlines():
            w = max(w, len(line))
            h += 1
        return w, h

    def set_text(self, textlist):
        """Text list is a list of tuples/lists
           There will be a line break between each item in textlist.
           The items themselves are lists alternating string and font.
        """
        # XXX tw, th = self.string_size(text)
        tw = 80
        th = 25

        self.textarea.config(state=tk.NORMAL, width=tw, height=th)
        self.textarea.delete('1.0', tk.END)      # enable editing

        for line in textlist:
            lineiter = iter(line)
            for text, font in zip(lineiter, lineiter):
                self.textarea.insert(tk.END, text, font)
            self.textarea.insert(tk.END, '\n')

        # self.textarea.insert(1.0, text)

        self.textarea.config(state=tk.DISABLED)  # back to read-only
        # self.focus_set()

    def popdown(self, event=None):
        self.withdraw()       # or iconify()

        # After dismissing the dialog, the focus tends to end up
        # in some random other window. Try to keep focus within the app:
        self._root().focus()
        # This seems like it should do the same thing,
        # but it doesn't actually focus the main window:
        # tk._default_root.focus()

    def destroy_func(self, event=None):
        # event=None necessary as we also use button binding.
        self.popdown()


#
# Custom messagebox, since messagebox doesn't allow for any additions
#

class CustomDialog(Dialog):
    def __init__(self, title, message, icon, buttons,
                 master=None, yes_bindings=[]):
        """
        icon can be "information", "warning", "error" or "question"
        buttons can be e.g. ["Yes", "No"], affirmative first
        """
        self.message = message
        self.icon = icon
        self.buttons = buttons
        self.yes_bindings = yes_bindings
        super().__init__(master, title)

    def body(self, parent):
        # get the system icon image
        # XXX the icons aren't working
        self.photo = tk.PhotoImage(master=parent)
        self.tk.call(self.photo, "copy", f"::tk::icons::{self.icon}")

        # create label with the icon image and message
        tk.Label(parent, text=self.message,
                 compound="left").pack(padx=50, pady=20)

    def buttonbox(self):
        box = tk.Frame(self)
        state = tk.NORMAL

        if not self.buttons:
            self.buttons = ["OK", "Cancel"]

        # The first button is equivalent to OK
        self.ok_btn = tk.Button(box, text=self.buttons[0],
                                width=20, command=self.ok,
                                default=tk.ACTIVE, state=state)
        self.ok_btn.pack(side=tk.LEFT, padx=5, pady=5)
        for btn_txt in self.buttons[1:-1]:
            btn = TkButton(box, text=btn_txt, width=20, command=button_callback,
                           default=tk.ACTIVE, state=state)
            btn.pack(side=tk.LEFT, padx=5, pady=5)

        # The last button is equivalent to Cancel, if more than one
        if len(self.buttons) > 1:
            self.cancel_btn = tk.Button(box, text=self.buttons[-1],
                                        width=20, state=state,
                                        command=self.cancel)
            self.cancel_btn.pack(side=tk.LEFT, padx=5, pady=5)

        box.pack()
        self._bindings()

    def button_callback(self, event):
        print("A button was pressed:", event)

    def _bindings(self):
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        for key in self.yes_bindings:
            self.bind(key, self.ok)

    def apply(self, event=None):
        self.result = True

    # def cancel(self, event=None):
    #     super().cancel(event)


def askyesno_with_bindings(title=None, message=None, yes_bindings=[]):
    dlg = CustomDialog(title=title, message=message, icon="question",
                       buttons=["Yes", "No"],
                       yes_bindings=yes_bindings)
    return dlg.result


def message_dialog(title=None, message=None, yes_bindings=[]):
    dlg = CustomDialog(title=title, message=message, icon="question",
                       buttons=["OK"], yes_bindings=yes_bindings)
    return dlg.result


# Flash a temporary message
def flash_message(msg, root):
    print(msg, file=sys.stderr)
    flashlbl = tk.Label(root, text=msg,
                        font=('',14), bg='yellow', relief=tk.SUNKEN)
    flashlbl.place(relx=.5, rely=.5, anchor=tk.CENTER)
    root.after(3000, flashlbl.destroy)


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

