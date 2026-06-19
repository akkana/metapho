#!/usr/bin/env python3

"""Test TkMetapho, at least the aspects of it I've managed to automate.
   Assumes X11, uses xdotool.
"""

import os
import time
import subprocess
import unittest

from Xlib import display, X

import sys, os
sys.path.insert(0, '..')

from metapho.tkpho.tk_tag_viewer import TkTagViewer


class TestTkMetaphoWindow(unittest.TestCase):
    def setUp(self):
        self.child_pid = None

    def tearDown(self):
        # if self.child_pid:
        #     os.kill(self.child_pid, 9)
        #     os.waitpid(self.child_pid, 0)

        # xdotool sometimes gets stuck after control keys, and the
        # ctrl key is never released, making it difficult to
        # get any control back.
        subprocess.run(['xdotool', 'keyup', 'ctrl'])

        pass

    def create_window(self, img_list, fixed_size=None):
        special_class_name = 'TkMetaphoTest'
        pid = os.fork()
        if pid == 0:
            tagger = TkTagViewer(img_list=img_list,
                                 class_name=special_class_name)
            tagger.root.mainloop()
            os._exit(0)

        # Parent process
        self.child_pid = pid

        self.original_focus = subprocess.run(
            ["xdotool", "getwindowfocus"],
            capture_output=True, text=True
        ).stdout.strip()

        time.sleep(1)
        self.window_id = int(subprocess.run(
            ["xdotool", "search", "--class", special_class_name],
            capture_output=True, text=True
        ).stdout)
        print("window_id is 0x%x = %d" % (self.window_id, self.window_id))

        # Focus doesn't always end up in the right window, so force it
        subprocess.run(["xdotool", "windowfocus", "--sync",
                        str(self.window_id)])

    def send_key(self, keyname, delay=1):
        """Send a key event to the window, with a short delay afterward.
           keyname is something like "space" or "a".
           Key names:
           https://gitlab.com/nokun/gestures/-/wikis/xdotool-list-of-key-codes
        """
        subprocess.run(["xdotool", "key", "--window",
                        str(self.window_id), keyname])
        time.sleep(delay)
        # subprocess.run(["xdotool", "keyup", "--window",
        #                 str(self.window_id), keyname])
        # time.sleep(delay)

    def close_window(self):
        # Quit.
        # For some reason, self.send_key("q") results in an endless
        # stream of 'q's to the terminal after the test exits,
        # and sending keyup after key, or sending type instead of key,
        # doesn't help. But this does:
        subprocess.run(["xdotool", "windowfocus", "--sync", str(self.window_id)])
        subprocess.run(["xdotool", "key", "--clearmodifiers", "q"])
        # restore focus
        subprocess.run(["xdotool", "windowfocus", "--sync",
                        str(self.original_focus)])
        time.sleep(1)


    def test_basic_window(self):
        # 1, 2, 3 are referenced in Tags, 4 is not.
        # Make sure there aren't any errors due to 2 and 3 not being
        # in the argument list.
        self.create_window([ "test/files/1.jpg",
                             "test/files/2.jpg",
                             "test/files/3.jpg",
                             "test/files/4.jpg",
                            ])

        time.sleep(1)

        # Closing the window with send_key(ctrl-q) results in
        # xdotool messing up the keyboard state so you get
        # qqqqqqqqqqqqqqqq repeating in the terminal where you ran the test,
        # and ctrl stuck on everywhere on the desktop.
        # But explicit keydown and keyup seem to work better.
        subprocess.run(["xdotool", "windowfocus", "--sync",
                        str(self.window_id)])
        subprocess.run(["xdotool", "keydown", 'ctrl'])
        subprocess.run(["xdotool", "keydown", 'q'])
        # self.send_key('ctrl+q')
        subprocess.run(["xdotool", "keyup", 'q'])
        subprocess.run(["xdotool", "keyup", 'ctrl'])

        # self.close_window()


if __name__ == "__main__":
    unittest.main()

