#!/usr/bin/env python3

# Tests for the notags helper for Metapho

import unittest

from pathlib import Path
import shutil
import os

import sys
sys.path.insert(0, '..')

from metapho import Image, Tagger, g_image_list


def sortlines(filecontents):
    """Given a long string meant to be the contents of a Tags file,
       sort the lines and remove blank lines.
    """
    lines = [ l for l in filecontents.split('\n') if l.strip() ]
    return '\n'.join(sorted(lines))


class NotagsTests(unittest.TestCase):

    # executed prior to each test
    def setUp(self):

        # XXX Image has a class variable, g_image_list,
        # holding all the images it knows about.
        # Re-using that between tests messes up the tests.
        g_image_list.clear()

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
        afile.write_text('tag tagged file: img1.jpg img2.jpg img5.jpg img6.jpg')

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

        abstestdir = os.path.abspath(self.testdir)

        nef = Image.find_nonexistent_files()
        utf, utd = tagger.find_untagged_files(self.testdir)

        nef.sort()
        self.assertEqual(nef, [os.path.join(abstestdir, 'dir1/img5.jpg'),
                               os.path.join(abstestdir, 'dir1/img6.jpg')])

        utf.sort()
        self.assertEqual(utf, [os.path.join(abstestdir, 'dir1/img3.jpg'),
                               os.path.join(abstestdir, 'dir1/img4.jpg')])

        self.assertEqual(utd, [os.path.join(abstestdir, 'dir2')])


    def test_dirtree(self):
        """Test tag files from several directories, by recursive dir,
           using read_tags(recursive=True).
        """
        abstestdir = os.path.abspath(self.testdir)

        tagfile = self.testdir / "dir2/Tags"
        tagfile.write_text("tag phred: imgb.jpg")
        tagfile = self.testdir / "Tags"
        tagfile.write_text("tag ann: dir1/img1.jpg dir2/imgc.jpg")

        tagger = Tagger()
        tagger.read_tags(self.testdir, recursive=True)

        self.assertEqual(tagger.commondir, abstestdir)

        self.assertEqual(sortlines(str(tagger)), """category Tags
tag ann : dir1/img1.jpg dir2/imgc.jpg
tag phred : dir2/imgb.jpg
tag tagged file : dir1/img1.jpg dir1/img2.jpg dir1/img5.jpg dir1/img6.jpg""")


    def test_dirtree_by_images(self):
        """Test tag files from several directories, by image list.
           This is how gtkpho's main initializes the tagger.
        """

        abstestdir = os.path.abspath(self.testdir)

        g_image_list.append(Image(os.path.join(abstestdir, "dir1/img1.jpg")))
        g_image_list.append(Image(os.path.join(abstestdir, "dir1/img2.jpg")))
        g_image_list.append(Image(os.path.join(abstestdir, "dir1/img3.jpg")))
        g_image_list.append(Image(os.path.join(abstestdir, "dir1/img4.jpg")))

        g_image_list.append(Image(os.path.join(abstestdir, "dir2/imga.jpg")))
        g_image_list.append(Image(os.path.join(abstestdir, "dir2/imgb.jpg")))
        g_image_list.append(Image(os.path.join(abstestdir, "dir2/imgc.jpg")))

        tagfile = self.testdir / "dir2/Tags"
        tagfile.write_text("tag phred: imgb.jpg")
        tagfile = self.testdir / "Tags"
        tagfile.write_text("tag ann: dir1/img1.jpg dir2/imgc.jpg")

        tagger = Tagger()
        tagger.read_all_tags_for_images()

        self.assertEqual(tagger.commondir, abstestdir)

        self.assertEqual(sortlines(str(tagger)), """category Tags
tag ann : dir1/img1.jpg dir2/imgc.jpg
tag phred : dir2/imgb.jpg
tag tagged file : dir1/img1.jpg dir1/img2.jpg""")


if __name__ == '__main__':
    unittest.main()

