#!/usr/bin/env python3

# Tests for the notags helper for Metapho

from __future__ import print_function

import unittest

from pathlib import Path
import shutil
import os

import sys
sys.path.insert(0, '..')

from metapho import Image, Tagger

class NotagsTests(unittest.TestCase):

    # executed prior to each test
    def setUp(self):

        # XXX Image has a class variable, g_image_list,
        # holding all the images it knows about.
        # Re-using that between tests messes up the tests.
        Image.g_image_list = []

        self.testdir = Path('test/testdir')
        self.testdir.mkdir()

        adir = self.testdir / "dir1"
        adir.mkdir()
        afile = self.testdir / "dir1/img1.jpg"
        afile.touch()
        afile = self.testdir / "dir1/img2.jpg"
        afile.touch()
        afile = self.testdir / "dir1/img3.jpg"
        afile.touch()
        afile = self.testdir / "dir1/img4.jpg"
        afile.touch()
        afile = self.testdir / "dir1/Tags"
        afile.write_text('''tag tagged file: img1.jpg img2.jpg img5.jpg img6.jpg''')

        adir = self.testdir / "dir2"
        adir.mkdir()
        afile = self.testdir / "dir2/imga.jpg"
        afile.touch()
        afile = self.testdir / "dir2/imgb.jpg"
        afile.touch()
        afile = self.testdir / "dir2/imgc.jpg"
        afile.touch()


    # executed after each test
    def tearDown(self):
        shutil.rmtree(self.testdir)


    def test_notags(self):
        """Test notags operations"""
        tagger = Tagger()
        tagger.read_tags(self.testdir)

        nef = Image.find_nonexistent_files()
        utf, utd = tagger.find_untagged_files(self.testdir)

        nef.sort()
        self.assertEqual(nef, ['test/testdir/dir1/img5.jpg',
                               'test/testdir/dir1/img6.jpg'])

        utf.sort()
        self.assertEqual(utf, ['test/testdir/dir1/img3.jpg',
                               'test/testdir/dir1/img4.jpg'])

        self.assertEqual(utd, ['test/testdir/dir2'])


    def test_dirtree(self):
        """Make sure the tagger can handle tag files from several directories.
        """

        with open(self.testdir / "dir2/Tags", 'w') as tagfp:
            print("""tag phred: imgb""", file=tagfp)
        with open(self.testdir / "Tags", 'w') as tagfp:
            print("""tag ann: dir1/img1 dir2/imgc""", file=tagfp)

        tagger = Tagger()
        tagger.read_tags(self.testdir)

        self.assertEqual(str(tagger), """
category Tags

tag phred : test/testdir/dir2/imgb
tag tagged file : test/testdir/dir1/img1.jpg test/testdir/dir1/img2.jpg test/testdir/dir1/img5.jpg test/testdir/dir1/img6.jpg
tag ann : test/testdir/dir1/img1 test/testdir/dir2/imgc
""")


if __name__ == '__main__':
    unittest.main()

