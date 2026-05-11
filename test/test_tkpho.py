#!/usr/bin/env python3

"""Test TkPho, at least the aspects of it I've managed to automate.
   Assumes X11, uses xdotool, may need screen size of 1920x1200.
"""

import os
import time
import subprocess
import unittest

from Xlib import display, X
from PIL import Image, ImageDraw

import sys, os
sys.path.insert(0, '..')

from metapho.tkpho import tkpho


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)


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
        self.assertFalse("Actual size %d x %d too different from expected "
                         "%d x %d" % (actual + expected))

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
        # I think this has been fixed by adding
        # borderwidth=0, highlightthickness=0
        # in the tk_label_widget constructor.
        # if autocrop:
        #     if ((width % 10 == 2 and height % 10 == 2) or
        #         (width == 1026 and height == 770)):
        #         image = image.crop((1, 1, width-1, height-1))

        # print("Made a screenshot, got an image that's", image.size)
        # image.show()

        return image.convert("RGB")

    @staticmethod
    def region_is_color(img, x, y, width, height, color,
                        tolerance=0, negate=False):
        """Does the indicated region match (or not match, if notcolor is True)
           the given color?
           If returning False, also print a summary and show images
           to show what's unexpected.
        """
        def print_color_summary():
            print("region_is_color:", x, y, width, height, color, "?")
            colorfreq = {}
            for py in range(y, y + height):
                for px in range(x, x + width):
                    # print(px, py, end=' -- ')
                    c = img.getpixel((px, py))
                    if c not in colorfreq:
                        colorfreq[c] = 1
                    else:
                        colorfreq[c] += 1
            print(colorfreq)

            cropimg = img.crop((x, y, x+width, y+height))
            # img.show() uses feh or another system-configured viewer.
            # Should probably use a tkpho window.

            draw = ImageDraw.Draw(img)
            linecolor = YELLOW
            draw.line((x, y, x+width, y), fill=linecolor)
            draw.line((x+width, y, x+width, y+height), fill=linecolor)
            draw.line((x, y, x, y+height), fill=linecolor)
            draw.line((x, y+height, x+width, y+height), fill=linecolor)

            img.show()
            cropimg.show()

        for py in range(y, y + height):
            for px in range(x, x + width):
                if any(abs(a - b) > tolerance
                       for a, b in zip(img.getpixel((px, py)), color)):
                    if negate:
                        return True
                    print_color_summary()
                    return False
        if not negate:
            return True
        print_color_summary()
        return False

    def test_basic_window(self):
        self.create_window([ "test/files/1.jpg",
                             "test/files/portrait.jpg",
                             "test/files/bigimg.png",
                             "test/files/bigcolorimg.png",
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
        self.assertTrue(self.region_is_color(screenshot,
                                             100, 100, 100, 100, RED))

        # Make sure double size doesn't work in fullsize mode
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (400, 300))
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot,
                                             100, 100, 100, 100, RED))

        # Get out of fullsize. The previous plus should have had no effect
        self.send_key("f")
        self.assert_compare_sizes(self.get_window_size(), (400, 300))
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot,
                                             100, 100, 100, 100, RED))

        # double size
        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (800, 600))
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot,
                                             200, 200, 200, 200, RED))

        # back to normal size, nonfullscreen, nonfullsize
        self.send_key("minus")

        # previous image, the big color image
        self.send_key("BackSpace", delay=2)
        self.assertEqual(self.get_window_title(),
                         "Pho: test/files/bigcolorimg.png (3000 x 2000)")
        self.assert_compare_sizes(self.get_window_size(), (1530, 1020))

        # fullscreen, fullsize
        self.send_key("p")
        self.send_key("f")

        # check the color squares
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot,
                                             60, 200, 200, 200, BLUE))

        # next image (colorsquares, not that that matters)
        sys.stdout.flush()
        self.send_key("space")

        # out of fullsize, still in fullscreen
        self.send_key("f")
        # back to big color image
        self.send_key("BackSpace")

        # Now bigcolorimg should be in fullscreen/non-fullsize.
        # Check for a bug where the scaled image wasn't getting reset.
        # The image should be scaled to the screen size now
        # with both color squares visible.
        screenshot = self.take_screenshot()
        self.assertTrue(self.region_is_color(screenshot,
                                              180, 120, 120, 120, RED))
        self.assertTrue(self.region_is_color(screenshot,
                                              420, 360, 120, 120, BLUE))

        # End of test
        self.close_window()

    def test_fixed_size_window(self):
        self.create_window([ "test/files/1.jpg",
                             "test/files/bigimg.png",
                             "test/files/colorsquares.png" ],
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

        # Next image, the big image, which shouldn't make the window any bigger
        self.send_key("space")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        # Fullsize shouldn't change the window size either
        self.send_key("f")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))
        self.send_key("f")

        # Move on to the colorsquares to check content
        self.send_key("space")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        # Take a screenshot and check some of the contents
        screenshot = self.take_screenshot()
        self.assertEqual(screenshot.size, (1024, 768))

        # The red square
        self.assertTrue(self.region_is_color(screenshot, 412, 334, 100, 100, RED))

        # The black left margin, where the image is smaller than the window
        self.assertTrue(self.region_is_color(screenshot, 0, 0, 312, 768, BLACK))
        self.send_key("f")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))

        self.send_key("f")

        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))
        screenshot = self.take_screenshot()
        # the black margin
        self.assertTrue(self.region_is_color(screenshot, 0, 0, 111, 768, BLACK))
        # The blue square
        self.assertTrue(self.region_is_color(screenshot, 512, 484, 200, 200,
                                             # ending up around 613, 627
                                             BLUE))

        self.send_key("plus")
        self.assert_compare_sizes(self.get_window_size(), (1024, 768))
        screenshot = self.take_screenshot()
        # the lower left white square -- there is no black margin
        self.assertTrue(self.region_is_color(screenshot, 0, 400, 400, 368, WHITE))
        # The red square
        self.assertTrue(self.region_is_color(screenshot, 400, 400, 400, 368, RED))
        # The green partial square
        self.assertTrue(self.region_is_color(screenshot, 800, 0, 224, 400, GREEN))

        self.close_window()

if __name__ == "__main__":
    unittest.main()
