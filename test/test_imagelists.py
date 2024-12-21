#!/usr/bin/env python3

# tests for metapho's image list


import unittest

import os

import metapho


class ImgListTests(unittest.TestCase):

    # executed prior to each test
    def setUp(self):
        pass

    # executed after each test
    def tearDown(self):
        pass

    def test_image_lists(self):
        for filename in os.listdir("test/files"):
            metapho.g_image_list.append(metapho.MetaphoImage(filename))

        # print(metapho.g_image_list)

        # There are 4 image files plus Tags and Tags.bak
        self.assertEqual(len(metapho.g_image_list), 6)

        # Admittedly we haven't tested this by actually trying to open them,
        # but metapho should at least know that Tags and Tags.bak
        # aren't images.
        self.assertEqual(metapho.num_displayed_images(), 4)
