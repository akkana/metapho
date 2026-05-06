#!/usr/bin/env python3

"""Test TkPho, at least the aspects of it I've managed to automate"""

import os
import time
import subprocess
import unittest

import sys, os
sys.path.insert(0, '..')

from metapho.tkpho import tkpho


class TestTkPhoWindow(unittest.TestCase):
    def setUp(self):
        self.child_pid = None

    def tearDown(self):
        # if self.child_pid:
        #     os.kill(self.child_pid, 9)
        #     os.waitpid(self.child_pid, 0)
        pass

    def get_window_size(self):
        result = subprocess.run(
            ["xdotool", "getwindowgeometry", str(self.window_id)],
            capture_output=True, text=True
        ).stdout
        geometry_line = [line for line in result.splitlines()
                         if line.strip().startswith("Geometry:")][0]
        width, height = geometry_line.split(":")[1].strip().split("x")
        width, height = int(width), int(height)
        return width, height

    def get_window_title(self):
        result = subprocess.run(
            ["xdotool", "getwindowname", str(self.window_id)],
            capture_output=True, text=True
        ).stdout.strip()
        return result

    def send_key(self, keyname, delay=1):
        """Send a key event to the window, with a short delay afterward.
           keyname is something like "space" or "a".
           Key names:
           https://gitlab.com/nokun/gestures/-/wikis/xdotool-list-of-key-codes
        """
        subprocess.run(["xdotool", "key", "--window", str(self.window_id), keyname])
        time.sleep(1)
        # subprocess.run(["xdotool", "keyup", "--window", str(self.window_id), keyname])
        # time.sleep(1)

    def assert_compare_sizes(self, actual, expected):
        """each is a (width, height) pair"""
        widthdiff = abs(actual[0] - expected[0])
        self.assertLess(widthdiff, 10)
        heightdiff = abs(actual[1] - expected[1])
        # titlebars take up a surprising amount of s
        self.assertLess(heightdiff, 60)

    def create_window(self, img_list, fixed_size=None):
        special_class_name = 'TkPhoTest'

        pid = os.fork()
        if pid == 0:
            # Child process: create and show the window
            pwin = tkpho.tkPhoWindow(
                parent=None,
                class_name=special_class_name,
                img_list=img_list, fixed_size=fixed_size)
            pwin.run()
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
        # print("window_id is 0x%x = %d" % (self.window_id, self.window_id))

    def test_basic_window(self):
        self.create_window([ "test/files/1.jpg",
                             "test/files/portrait.jpg",
                             "test/files/bigimg.png" ])

        # Check window size.
        # It will be a little off due to windowmanager decorations.
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (640, 480))

        # Send space key to move to next image
        self.send_key("space")

        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (480, 640))

        # Check title
        title = self.get_window_title()
        self.assertEqual(title, "Pho: test/files/portrait.jpg (480 x 640)")

        # Send right arrow to rotate
        self.send_key("Right")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (640, 480))

        # half size
        self.send_key("minus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (320, 240))

        # normal size
        self.send_key("plus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (640, 480))

        # double size
        self.send_key("plus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (1280, 960))

        # normal size
        self.send_key("minus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (640, 480))

        # Try fullscreen
        self.send_key("p")
        width, height = self.get_window_size()
        # Lazy, not loading Tk libraries to get the actual screen size
        self.assertGreater(width, 1023)
        self.assertGreater(height, 767)

        # Out of fullscreen
        self.send_key("p")
        # When coming out of fullscreen, focus is often lost,
        # and despite specifying the windowid to xdotool,
        # that actually doesn't work and it sends the character
        # to the currently focused window instead. So put focus back.
        subprocess.run(["xdotool", "windowfocus", "--sync", str(self.window_id)])
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (640, 480))

        # Go to the big image. Use a longer delay because loading/scaling
        # may take a little longer.
        self.send_key("space", delay=2)
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (1530, 1020))

        self.send_key("f")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (3000, 2000))

        # Go back. The previous image is still rotated and we're
        # still in fullsize mode, but it's small so that's okay.
        self.send_key("BackSpace")
        title = self.get_window_title()
        self.assertEqual(title, "Pho: test/files/portrait.jpg (480 x 640)")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (640, 480))

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

    def test_fixed_size_window(self):
        self.create_window([ "test/files/1.jpg",
                             "test/files/bigimg.png" ],
                           fixed_size=[1024, 768])

        # Check window size.
        width, height = self.get_window_size()
        print("window size is", width, height)
        self.assert_compare_sizes((width, height), (1024, 768))

        # half size
        self.send_key("minus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (1024, 768))

        # normal size
        self.send_key("plus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (1024, 768))

        # double size
        self.send_key("plus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (1024, 768))

        # normal size
        self.send_key("minus")
        width, height = self.get_window_size()
        self.assert_compare_sizes((width, height), (1024, 768))

        # Quit.
        subprocess.run(["xdotool", "windowfocus", "--sync", str(self.window_id)])
        subprocess.run(["xdotool", "key", "--clearmodifiers", "q"])
        # restore focus
        subprocess.run(["xdotool", "windowfocus", "--sync",
                        str(self.original_focus)])
        time.sleep(1)


if __name__ == "__main__":
    unittest.main()
