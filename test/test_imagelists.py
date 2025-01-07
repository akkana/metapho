#!/usr/bin/env python3

# tests for metapho's image list


import unittest

import os

from metapho import imagelist, MetaphoImage


class ImgListTests(unittest.TestCase):

    # executed prior to each test
    def setUp(self):
        pass

    # executed after each test
    def tearDown(self):
        pass

    def test_image_lists(self):
        imagelist.add_images([ MetaphoImage(f)
                               for f in os.listdir("test/files") ])

        # print(metapho.g_image_list)

        # There are 4 image files plus Tags and Tags.bak
        self.assertEqual(imagelist.num_images(), 6)

        # Admittedly we haven't tested this by actually trying to open them,
        # but metapho should at least know that Tags and Tags.bak
        # aren't images.
        self.assertEqual(imagelist.num_valid_images(), 4)
