#!/usr/bin/env python

# Copyright 2013,2016,2019 by Akkana Peck:
# share and enjoy under the GPL v2 or later.

"""
These are the base class for metapho images and taggers.
Programs with better UI can inherit from these classes.

"""

# MetaphoImage and Tagger classes have to be defined here in order for
# other files to be able to use them as metapho.MetaphoImage rather than
# metapho.MetaphoImage.MetaphoImage. I haven't found any way that lets me split
# the classes into separate files. Sigh!

import sys, os


# A list of all the filenames the program knows about.
g_image_list = []

# The image list has both displayed and nondisplayed images,
# because it's possible to run metapho on a subset of images in a directory,
# to change or add tags on only those images, but there may be an existing
# Tags file in the directory covering the other images, and we wouldn't
# want to forget their tags.
# XXX would this be any faster as a generator comprehension?
def displayed_images():
    return [ im for im in g_image_list if im.displayed and not im.invalid ]

def num_displayed_images():
    return len(displayed_images())

def find_in_displayed_images():
    """Return index, total"""
    imgs = displayed_images()
    return index, len(imgs)

def num_hidden_images():
    return len(( i for i in g_image_list if not i.displayed ))

def num_total_images():
    return len(g_image_list)


class MetaphoImage:
    """An image, with additional info such as rotation and tags.
    """

    def __init__(self, filename, displayed=True):
        """Initialize an image filename.
           Pass displayed=False if this image isn't to be shown
           in the current session, only used for remembering
           previously set tags.
        """
        # filename is an absolute path
        self.filename = os.path.abspath(filename)

        # But it's useful to remember relative path too
        self.relpath = filename

        self.tags = []

        self.displayed = displayed

        # Some filenames, like Tags, are known not to be images.
        # In other cases, an image that can't be opened also
        # shouldn't be considered as an image since it will never
        # be shown to the user. Start out by assuming everything's valid
        # except Tags*.
        if ((filename.startswith("Tags") or filename.startswith("Keywords"))
            and ("." not in filename or filename.endswith(".bak"))):
            self.invalid = True
        else:
            # For anything else, start out assuming it's okay
            self.invalid = False

        # Rotation of the image relative to what it is on disk.
        # None means we don't know yet, 0 means stay at 0.
        # Note: use 270 for counter-clockwise rotation, not -90.
        self.rot = None

    def __repr__(self):
        str = "MetaphoImage '%s'" % self.relpath

        if self.rot:
            str += " (rotation %s)" % self.rot

        if self.tags:
            str += ": Tags: " + self.tags.__repr__()

        # str += '\n'

        return str

    def __eq__(self, other):
        if hasattr(other, 'filename') and hasattr(other, 'tags'):
            return self.filename == other.filename and self.tags == other.tags
        return other == self.filename

    def __lt__(self, other):
        return self.filename < other.filename

    def __gt__(self, other):
        return self.filename > other.filename

    def __le__(self, other):
        return self.filename <= other.filename

    def __ge__(self, other):
        return self.filename >= other.filename

    def delete(self):
        """Delete the image file FROM DISK, and the image object
           from the imageList. DOES NOT ASK FOR CONFIRMATION --
           do that (if desired) from the calling program.
        """
        print("Deleting", self.filename)
        os.unlink(self.filename)
        g_image_list.remove(self)

    @classmethod
    def image_index(cls, filename):
        """Find a name in the global image list. Return index, or None."""
        if not self.invalid:
            return None
        for i, img in enumerate(g_image_list):
            if img.filename == filename:
                return i
        return None

    @classmethod
    def find_nonexistent_files(cls):
        """Returns a list of images in the imagelist that don't exist on disk.
        """
        not_on_disk = set()
        for im in g_image_list:
            if not os.path.exists(im.filename):
                not_on_disk.add(im.filename)
        not_on_disk = list(not_on_disk)
        not_on_disk.sort()
        return not_on_disk

    @classmethod
    def clean_up_nonexistent_files(cls, topdir):
        """For any file that was referenced in a tag file but doesn't
           exist on disk, see if perhaps it's been moved to a different
           subdirectory under topdir. If so, adjust file path appropriately.
        """
        nefbases = set()
        nefdict = {}
        for f in cls.find_nonexistent_files():
            fbase = os.path.basename(f)
            nefbases.add(fbase)
            if fbase in nefdict:
                print("Warning: multiple files named", fbase)
            else:
                nefdict[fbase] = f

        for root, dirs, files in os.walk(topdir):
            root = os.path.normpath(root)
            for f in files:
                if f in nefbases:
                    try:
                        i = cls.image_index(nefdict[f])
                        g_image_list[i].filename = os.path.join(root, f)
                    except ValueError:
                        print("Eek!", nefdict[f], \
                            "has vanished from the global image list")

                    nefbases.remove(f)

        # Now we've adjusted paths for any file that's moved.
        # But what about files that have simply been removed?
        # Those are still in nefbases.
        if nefbases:
            # print("Removing missing files from Tags file:", \
            #     ' '.join([nefdict[f] for f in nefbases]))
            for f in nefbases:
                g_image_list.remove(nefdict[f])

if __name__ == '__main__':
    main()
