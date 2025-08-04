#!/usr/bin/env python

# Copyright 2013,2016,2019,2024 by Akkana Peck:
# share and enjoy under the GPL v2 or later.

"""
The base class for metapho images.
Programs with a GUI can inherit from MetaphoImage.
"""

from collections import defaultdict
import sys, os

from . import imagelist


# The image list has both displayed and nondisplayed images,
# because it's possible to run metapho on a subset of images in a directory,
# to change or add tags on only those images, but there may be an existing
# Tags file in the directory covering the other images, and we wouldn't
# want to forget their tags.
# XXX would this be any faster as a generator comprehension?
def displayed_images():
    return [ im for im in imagelist.image_list()
             if im.displayed and not im.invalid ]

def num_displayed_images():
    return len(displayed_images())

def find_in_displayed_images():
    """Return index, total"""
    imgs = displayed_images()
    return index, len(imgs)

def num_hidden_images():
    return len(( i for i in imagelist.image_list() if not i.displayed ))

def num_total_images():
    return imagelist.num_images()


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

        basename = os.path.basename(filename)

        # A list of indices into the tagger's tag_list.
        self.tags = []

        self.displayed = displayed

        # Some filenames, like Tags, are known not to be images.
        # In other cases, an image that can't be opened also
        # shouldn't be considered as an image since it will never
        # be shown to the user.
        # That also applies to images that were omitted on the commandline,
        # even if they would otherwise have been valid.
        # Start out by assuming everything's valid except Tags*.
        if ((basename.startswith("Tags") or basename.startswith("Keywords"))
            and ("." not in basename or basename.endswith(".bak"))):
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

        if self.invalid:
            str += " (invalid)"

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
        imagelist.remove_image(self)

    def toggle_tag(self, tagno):
        """This is only called from gtk metapho and tkpho.
           Tk metapho has its own toggle handler.
           tagno should be a string, the actual tag.
        """
        if tagno in self.tags:
            self.tags.remove(tagno)
        else:
            self.tags.append(tagno)

    def add_tag(self, tagno):
        if tagno in self.tags:
            return
        self.tags.append(tagno)

    def remove_tag(self, tagno):
        try:
            self.tags.remove(tagno)
        except ValueError:
            pass

    @classmethod
    def tagged_images(cls):
        """Return a dictionary of { tag: [list of tagged images] }
        """
        alltagged = defaultdict(list)
        for img in imagelist.image_list():
            for tag in img.tags:
                alltagged[tag].append(img)
        return alltagged

    @classmethod
    def image_index(cls, filename):
        """Find a name in the global image list. Return index, or None."""
        for i, img in enumerate(imagelist.image_list()):
            if img.filename == filename and not img.invalid:
                return i
        return None

    @classmethod
    def find_nonexistent_files(cls):
        """Returns a list of images in the imagelist that don't exist on disk.
        """
        not_on_disk = set()
        for im in imagelist.image_list():
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
                        imagelist.get_image(i).filename = os.path.join(root, f)
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
                imagelist.remove_image(nefdict[f])

if __name__ == '__main__':
    main()
