#!/usr/bin/env python3

# Tests for the notags helper for Metapho

import unittest

from pathlib import Path
import shutil
import os

import sys
sys.path.insert(0, '..')

from metapho import MetaphoImage, Tagger, imagelist


def sortlines(filecontents):
    """Given a long string meant to be the contents of a Tags file,
       sort the lines and remove blank lines.
    """
    lines = [ l for l in filecontents.split('\n') if l.strip() ]
    return '\n'.join(sorted(lines))


class NotagsTests(unittest.TestCase):

    # executed prior to each test
    def setUp(self):

        # XXX The imagelist is global,
        # holding all the images it knows about.
        # Re-using that between tests would mess up the tests.
        imagelist.clear_images()

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

    def setUpMultilevel(self):
        adir = self.testdir / "dir3"
        adir.mkdir()
        adir = self.testdir / "dir3/subdir1"
        adir.mkdir()
        adir = self.testdir / "dir3/subdir2"
        adir.mkdir()
        afile = self.testdir / "dir3/subdir1/imga.jpg"
        afile.touch()
        afile = self.testdir / "dir3/subdir1/imgb.jpg"
        afile.touch()
        afile = self.testdir / "dir3/subdir2/imga.jpg"
        afile.touch()
        afile = self.testdir / "dir3/subdir2/imgb.jpg"
        afile.touch()
        afile = self.testdir / "dir3/Tags"
        afile.write_text('tag tagged file: subdir1/imga.jpg')


    def test_multilevel(self):
        """Test that tags from a parent dir are seen as applying to subdirs
        """
        self.setUpMultilevel()
        tagger = Tagger()
        tagger.read_tags(self.testdir)

        abstestdir = os.path.abspath(self.testdir)

        utf, utd = tagger.find_untagged_files(self.testdir)
        self.assertTrue(os.path.join(abstestdir, 'dir3/subdir2') in utd)
        self.assertTrue(os.path.join(abstestdir, 'dir3/subdir1/imga.jpg')
                        not in utf)
        self.assertTrue(os.path.join(abstestdir, 'dir3/subdir1/imgb.jpg')
                        in utf)


    # executed after each test
    def tearDown(self):
        shutil.rmtree(self.testdir)


    def test_notags(self):
        """Test notags operations"""
        tagger = Tagger()
        tagger.read_tags(self.testdir)

        abstestdir = os.path.abspath(self.testdir)

        nef = MetaphoImage.find_nonexistent_files()
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

        imagelist.add_images(MetaphoImage(os.path.join(abstestdir,
                                                      "dir1/img1.jpg")))
        imagelist.add_images(MetaphoImage(os.path.join(abstestdir,
                                                      "dir1/img2.jpg")))
        imagelist.add_images(MetaphoImage(os.path.join(abstestdir,
                                                      "dir1/img3.jpg")))
        imagelist.add_images(MetaphoImage(os.path.join(abstestdir,
                                                      "dir1/img4.jpg")))

        imagelist.add_images(MetaphoImage(os.path.join(abstestdir,
                                                      "dir2/imga.jpg")))
        imagelist.add_images(MetaphoImage(os.path.join(abstestdir,
                                                      "dir2/imgb.jpg")))
        imagelist.add_images(MetaphoImage(os.path.join(abstestdir,
                                                      "dir2/imgc.jpg")))

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

