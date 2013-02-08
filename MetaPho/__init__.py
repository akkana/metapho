#!/usr/bin/env python

# MetaPho: an image tagger and viewer.

# Copyright 2013 by Akkana Peck: share and enjoy under the GPL v2 or later.

# Every MetaPho program will need MetaPho Images and Taggers.
# Everything else is probably optional.

'''MetaPho: an image tagger and viewer.'''

__version__ = "0.1"
__author__ = "Akkana Peck <akkana@shallowsky.com>"
__license__ = "GPL v2"
__all__ = [ 'Image', 'Tagger' ]

# Image and Tagger classes have to be defined here in order for
# other files to be able to use them as MetaPho.Image rather than
# MetaPho.Image.Image. I haven't found any way that lets me split
# the classes into separate files. Sigh!

class Image :
    '''An image, with additional info such as rotation and tags.
       Eventually methods like delete() to delete the file from disk
       will probably also live in this class.
    '''

    gImageList = []

    def __init__(self, filename) :
        self.filename = filename
        self.tags = []
        self.rot = None      # None means we don't know yet, 0 means stay at 0
        # Note: use 270 for counter-clockwise rotation, not -90.

    def __repr__(self) :
        str = "Image %s" % self.filename

        if self.rot :
            str += " (rotation %s)" % self.rot

        if self.tags :
            str += " Tags: " + self.tags.__repr__()

        str += '\n'

        return str

    # Next two perhaps belong in Tagger, not here.
    def addTag(self, tag) :
        '''Add a tag to this image.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index of the tag just added, or None if error.
        '''
        return None

    def matchTag(self, pattern) :
        '''Return a list of tags matching the pattern.'''
        return None

import os
import shlex

class Tagger(object) :
    '''Manages tags for images.
    '''

    gTagList = []
    '''The list of tags is common to every image in the application.
    '''

    def __init__(self) :
        '''imagelist: a list of MetaPho Images'''
        pass

    def readTags(self, dirname) :
        '''Read in tags from files named in the given directory,
           and tag images in the imagelist appropriately.
           Tags will be appended to Tagger.gTagList.
        '''
        # Might want to be recursive and use os.walk ...
        # or maybe go the other way, search for Tags files
        # *above* the current directory but not below.
        # For now, only take the given directory.
        '''off-the-cuff example format:
tagtype People: Alice, Bill, Charlie, Dennis
tagtype Places: America, Belgium, Czech Republic, Denmark
photo p103049.jpg: Alice, Belgium
photo p103050.jpg: Charlie, Denmark
photo p103051.jpg: Charlie, Bill, Denmark
tag Alice: p103049.jpg
tag Belgium: p103049.jpg
tag Bill: p103051.jpg
tag Charlie: p103050.jpg, p103051.jpg
tag Denmark: p103050.jpg, p103051.jpg
        '''
        try :
            pathname = os.path.join(dirname, "Tags")
            fp = open(pathname)
            print "Opened", pathname
        except IOError :
            try :
                pathname = os.path.join(dirname, "Keywords")
                fp = open(pathname)
            except IOError :
                print "No Tags file in", dirname
                return

        for line in fp :
            colon = line.find(':')
            if colon < 0 :
                continue    # If there's no colon, it's not a legal tag line

            # Now we know we have tagname, typename or photoname.
            # Get the list of objects after the colon.
            # Use shlex to handle quoted and backslashed
            # filenames with embedded spaces.
            try :
                objects = shlex.split(line[colon+1:].strip())
            except ValueError:
                print pathname, "Couldn't parse:", line
                continue

            if line.startswith('tag ') :
                tagname = line[4:colon].strip()
                print "Tag", tagname, ": objects", objects
                self.processTag(tagname, objects)

            elif line.startswith('tagtype ') :
                typename = line[8:colon].strip()

            elif line.startswith('photo ') :
                photoname = line[6:colon].strip()

            else :
                # Assume it's a tag: file file file line
                tagname = line[:colon].strip()
                print "Keyword", tagname, ": objects", objects
                self.processTag(tagname, objects)

        fp.close()

    def processTag(self, tagname, filenames) :
        '''After reading a tag from a tags file, add it to the global
           tags list if it isn't there already, and add the given filenames
           to it.
        '''
        try :
            tagindex = Tagger.gTagList.index(tagname)
        except :
            tagindex = len(Tagger.gTagList)
            Tagger.gTagList.append(tagname)

        # Search for images matching the names in filenames
        # XXX pathname issue here: filenames in tag files generally don't
        # have absolute pathnames, so we're only matching basenames and
        # there could be collisions.
        for img in Image.gImageList :
            for fil in filenames :
                if img.filename.endswith(fil) and tagindex not in img.tags :
                    img.tags.append(tagindex)

    def setImage(self, img) :
        '''Set the current image to img (a MetaPho Image).
           Load the associated tags, and (in derived classes) show them
           in whatever way is appropriate.
        '''
        print "Current", img
        print "Current tags:", img.tags
        for tagindex in img.tags :
            print "  ", Tagger.gTagList[tagindex]
