#!/usr/bin/env python3

# Tests for the notags helper for Metapho

from __future__ import print_function

import unittest

from pathlib import Path
import shutil

import sys
sys.path.insert(0, '..')

from metapho import Image, Tagger

class NotagsTests(unittest.TestCase):

    # executed prior to each test
    def setUp(self):
        self.testdir = Path('test/testdir')
        self.testdir.mkdir()

        adir = Path('test/testdir/dir1')
        adir.mkdir()
        afile = Path('test/testdir/dir1/img1.jpg')
        afile.touch()
        afile = Path('test/testdir/dir1/img2.jpg')
        afile.touch()
        afile = Path('test/testdir/dir1/img3.jpg')
        afile.touch()
        afile = Path('test/testdir/dir1/img4.jpg')
        afile.touch()
        afile = Path('test/testdir/dir1/Tags')
        afile.write_text('''tag tagged file: img1.jpg img2.jpg img5.jpg img6.jpg''')

        adir = Path('test/testdir/dir2')
        adir.mkdir()
        afile = Path('test/testdir/dir2/imga.jpg')
        afile.touch()
        afile = Path('test/testdir/dir2/imgb.jpg')
        afile.touch()
        afile = Path('test/testdir/dir2/imgc.jpg')
        afile.touch()


    # executed after each test
    def tearDown(self):
        shutil.rmtree(self.testdir)


    def test_notags(self):
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


if __name__ == '__main__':
    unittest.main()

