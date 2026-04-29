#!/usr/bin/env python3

"""Test TkPho, at least the aspects of it I've managed to automate"""

import os
import time
import subprocess
import unittest

import sys, os
sys.path.insert(0, '..')

from metapho.tkpho import tkpho

def get_window_size(window_id):
    result = subprocess.run(
        ["xdotool", "getwindowgeometry", str(window_id)],
        capture_output=True, text=True
    ).stdout
    geometry_line = [line for line in result.splitlines()
                     if line.strip().startswith("Geometry:")][0]
    width, height = geometry_line.split(":")[1].strip().split("x")
    width, height = int(width), int(height)
    return width, height

def get_window_title(window_id):
    result = subprocess.run(
        ["xdotool", "getwindowname", str(window_id)],
        capture_output=True, text=True
    ).stdout.strip()
    return result

def send_key(window_id, keyname):
    """Send a key event to the window.
       keyname is something like "space" or "a".
       Key names:
       https://gitlab.com/nokun/gestures/-/wikis/xdotool-list-of-key-codes
    """
    subprocess.run(["xdotool", "key", "--window", str(window_id), keyname])
    # subprocess.run(["xdotool", "keyup", "--window", str(window_id), keyname])



class TestTkPhoWindow(unittest.TestCase):
    def setUp(self):
        self.child_pid = None

    def tearDown(self):
        # if self.child_pid:
        #     os.kill(self.child_pid, 9)
        #     os.waitpid(self.child_pid, 0)
        pass

    def assert_compare_sizes(self, actual, expected):
        """each is a (width, height) pair"""
        widthdiff = abs(actual[0] - expected[0])
        self.assertLess(widthdiff, 10)
        heightdiff = abs(actual[1] - expected[1])
        # titlebars take up a surprising amount of s
        self.assertLess(heightdiff, 60)

    def test_window(self):
        special_class_name = 'TkPhoTest'

        pid = os.fork()
        if pid == 0:
            # Child process: create and show the window
            pwin = tkpho.tkPhoWindow(
                parent=None,
                class_name=special_class_name,
                img_list=["test/files/1.jpg", "test/files/portrait.jpg"]
            )
            pwin.run()
            os._exit(0)

        # Parent process
        self.child_pid = pid

        time.sleep(1)
        window_id = int(subprocess.run(
            ["xdotool", "search", "--class", special_class_name],
            capture_output=True, text=True
        ).stdout)
        # print("window_id is 0x%x = %d" % (window_id, window_id))

        # Check window size.
        # It will be a little off due to windowmanager decorations.
        width, height = get_window_size(window_id)
        # print("Actual size:", width, "x", height)
        self.assert_compare_sizes((width, height), (640, 480))

        # Send space key to move to next image
        send_key(window_id, "space")
        time.sleep(1)

        width, height = get_window_size(window_id)
        self.assert_compare_sizes((width, height), (480, 640))

        # Check title
        title = get_window_title(window_id)
        # print("Actual title: '%s'" % title)
        self.assertEqual(title, "Pho: test/files/portrait.jpg (480 x 680)")

        # # Send right arrow to rotate
        # send_key(window_id, "Right")
        # time.sleep(1)
        # width, height = get_window_size(window_id)
        # self.assert_compare_sizes((width, height), (640, 480))

        time.sleep(2)
        print("Quitting ...")
        # For some reason, send_key(window_id, "q") results in an endless
        # stream of 'q's to the terminal after the test exits,
        # and sending keyup after key, or sending type instead of key,
        # doesn't help.
        original_focus = subprocess.run(
            ["xdotool", "getwindowfocus"],
            capture_output=True, text=True
        ).stdout.strip()
        subprocess.run(["xdotool", "windowfocus", "--sync", str(window_id)])
        subprocess.run(["xdotool", "key", "--clearmodifiers", "q"])
        # restore focus
        subprocess.run(["xdotool", "windowfocus", "--sync", str(original_focus)])

if __name__ == "__main__":
    unittest.main()
