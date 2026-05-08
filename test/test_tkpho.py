#!/usr/bin/env python3

"""Test TkPho, at least the aspects of it I've managed to automate"""

import os
import time
import subprocess
import unittest

from Xlib import display, X
from PIL import Image

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

    def get_window_title(self):
        result = subprocess.run(
            ["xdotool", "getwindowname", str(self.window_id)],
            capture_output=True, text=True
        ).stdout.strip()
        return result

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

    def send_key(self, keyname, delay=1):
        """Send a key event to the window, with a short delay afterward.
           keyname is something like "space" or "a".
           Key names:
           https://gitlab.com/nokun/gestures/-/wikis/xdotool-list-of-key-codes
        """
        subprocess.run(["xdotool", "key", "--window",
                        str(self.window_id), keyname])
        time.sleep(1)
        # subprocess.run(["xdotool", "keyup", "--window",
        #                 str(self.window_id), keyname])
        # time.sleep(1)

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

    def assert_compare_sizes(self, actual, expected):
        """each is a (width, height) pair.
        """
        # width diff
        if (abs(actual[0] - expected[0]) < 10 and
            # height difference: titlebars take up a surprising amount of space
            abs(actual[1] - expected[1]) < 60):
            return
        # I haven't found a way to write a unittest assert and control
        # its output, so this is a hack.
        self.assertFalse("Actual size %d x %d too different from expected %d x %d"
                         % (actual + expected))

    def take_screenshot(self):
        """
        Capture the contents of the current X11 window by its window ID.

        Returns:
            A PIL Image of the window's current contents.
        """
        d = display.Display()
        window = d.create_resource_object("window", self.window_id)

        # Get window geometry (size and position relative to its parent)
        geom = window.get_geometry()
        width, height = geom.width, geom.height

        # Capture the window contents via XGetImage
        raw = window.get_image(0, 0, width, height, X.ZPixmap, 0xFFFFFFFF)

        # XGetImage returns 32-bit BGRX data; convert to RGBA then RGB
        image = Image.frombytes(
            "RGBA",
            (width, height),
            raw.data,
            "raw",
            "BGRA",
        )
        width, height = image.size
        # tk is adding a one-pixel border, and I'm okay with that,
        # but it throws off the checking of contents.
        if width % 10 == 2 and height % 10 == 2:
            image = image.crop((1, 1, width-1, height-1))

        return image.convert("RGB")

    @staticmethod
    def region_is_color(img, x, y, width, height, color, tolerance=0):
        def print_color_summary():
            colorfreq = {}
            for py in range(y, y + height):
                for px in range(x, x + width):
                    c = img.getpixel((px, py))
                    if c not in colorfreq:
                        colorfreq[c] = 1
                    else:
                        colorfreq[c] += 1
            print(colorfreq)

        for py in range(y, y + height):
            for px in range(x, x + width):
                if any(abs(a - b) > tolerance
                       for a, b in zip(img.getpixel((px, py)), color)):
                    print_color_summary()
                    return False
        return True

    def test_basic_window(self):
        self.create_window([ "test/files/1.jpg",
                             "test/files/portrait.jpg",
                             "test/files/bigimg.png",
                             "test/files/colorsquares.png",
                            ])

        # Check window size.
        # It will be a little off due to windowmanager decorations.
        self.assert_compare_sizes(self.get_window_size(), (640, 480))

        # Send space key to move to next image
        self.send_key("space")

        self.assert_compare_sizes(self.get_window_size(), (480, 640))

        # Check title
        self.assertEqual(self.get_window_title(),
                         "Pho: test/files/portrait.jpg (480 x 640)")

        # Send right arrow to rotate
        self.send_key("Right")
        self.assert_compare_sizes(self.get_window_size(), (640, 480))

        # half size
        self.send_key("minus")
        self.assert_compare_sizes(self.get_window_size(), (320, 240))

        # normal size
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (640, 480))

        # double size
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (1280, 960))

        # normal size
        self.send_key("minus")
        self.assert_compare_sizes(self.get_window_size(), (640, 480))

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
        self.assert_compare_sizes(self.get_window_size(), (640, 480))

        # Go to the big image. Use a longer delay because loading/scaling
        # may take a little longer.
        self.send_key("space", delay=2)
        self.assert_compare_sizes(self.get_window_size(), (1530, 1020))

        self.send_key("f")
        self.assert_compare_sizes(self.get_window_size(), (3000, 2000))

        # Go back. The previous image is still rotated and we're
        # still in fullsize mode, but it's small so that's okay.
        self.send_key("BackSpace")
        self.assertEqual(self.get_window_title(),
                         "Pho: test/files/portrait.jpg (480 x 640)")
        self.assert_compare_sizes(self.get_window_size(), (640, 480))

        # Move to the colorsquares image, still in fullsize
        self.send_key("End")
        self.assertEqual(self.get_window_title(),
                         "Pho: test/files/colorsquares.png (400 x 300)")
        self.assert_compare_sizes(self.get_window_size(), (400, 300))

        # Take a screenshot and check some of the contents
        screenshot = self.take_screenshot()
        self.assertEqual(screenshot.size, (400, 300))
        self.assertTrue(self.region_is_color(screenshot, 100, 100, 100, 100,
                                              (255, 0, 0)))

        # Make sure double size doesn't work in fullsize mode
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (400, 300))
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot, 100, 100, 100, 100,
                                              (255, 0, 0)))

        # Get out of fullsize. The previous plus should have had no effect
        self.send_key("f")
        self.assert_compare_sizes(self.get_window_size(), (400, 300))
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot, 100, 100, 100, 100,
                                              (255, 0, 0)))

        # double size
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (800, 600))
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot, 200, 200, 200, 200,
                                              (255, 0, 0)))

        self.close_window()

    def test_fixed_size_window(self):
        self.create_window([ "test/files/1.jpg",
                             "test/files/bigimg.png" ],
                           fixed_size=[1024, 768])

        # Check window size.
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        # half size
        self.send_key("minus")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        # normal size
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        # double size
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        # normal size
        self.send_key("minus")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        # Take a screenshot and check some of the contents
        screenshot = self.take_screenshot()
        # print("Made a screenshot, got an image that's", screenshot.size)
        # screenshot.show()

        # Thick black band on the left edge, where the image is
        # smaller than the window
        self.assertTrue(self.region_is_color(screenshot, 0, 0, 192, 480,
                                              (0, 0, 0)))
        # The white left edge of the image, left of where the numeral 1 is
        self.assertTrue(self.region_is_color(screenshot, 194, 145, 200, 478,
                                              (255, 255, 255)))

        self.close_window()


if __name__ == "__main__":
    unittest.main()
