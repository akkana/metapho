#!/usr/bin/env python

# Base classes for MetaPho: an image tagger and viewer.

# Copyright 2013 by Akkana Peck: share and enjoy under the GPL v2 or later.

# Image and Tagger classes have to be defined here in order for
# other files to be able to use them as MetaPho.Image rather than
# MetaPho.Image.Image. I haven't found any way that lets me split
# the classes into separate files. Sigh!

import os
import collections    # for OrderedDict

class Image :
    '''An image, with additional info such as rotation and tags.
    '''

    g_image_list = []

    def __init__(self, filename, displayed=True) :
        '''Initialize an image filename.
           Pass displayed=False if this image isn't to be shown
           in the current session, only used for remembering
           previously set tags.
        '''
        self.filename = filename
        self.tags = []

        self.displayed = displayed

        # Rotation of the image relative to what it is on disk.
        # None means we don't know yet, 0 means stay at 0.
        # Note: use 270 for counter-clockwise rotation, not -90.
        self.rot = None

    def __repr__(self) :
        str = "Image %s" % self.filename

        if self.rot :
            str += " (rotation %s)" % self.rot

        if self.tags :
            str += " Tags: " + self.tags.__repr__()

        str += '\n'

        return str

    def delete(self) :
        '''Delete the image file FROM DISK, and the image object
           from the imageList. DOES NOT ASK FOR CONFIRMATION --
           do that (if desired) from the calling program.
        '''
        print "Deleting", self.filename
        os.unlink(self.filename)
        Image.g_image_list.remove(self)

import shlex

class Tagger(object) :
    '''Manages tags for images.
    '''

    def __init__(self) :
        '''tagger: an object to manage MetaPho image tags'''

        # The category list is a list of lists:
        # [ [ "First category", 3, 5, 11 ] ]
        # means category 0 has the name "First category" and includes
        # tags 3, 5 and 11 from the tag_list.
        self.categories = collections.OrderedDict()

        # The tag list is just a list of all tags we know about.
        # A tag may be in several categories.
        self.tag_list = []

        # Files from which we've read tags
        self.tagfiles = []
        # the directory common to them, where we'll try to store tags
        self.commondir = None

        # Have any tags changed during this run?
        # Don't update the Tags file if the user doesn't change anything.
        self.changed = False

        # What category are we currently processing? Default is Tags.
        self.current_category = "Tags"

    def __repr__(self) :
        '''Returns a string summarizing all known images and tags,
           suitable for printing on stdout or pasting into a Tags file.
        '''
        outstr = ''
        for cat in self.categories :
            outstr += '\ncategory ' + cat + '\n\n'

            for tagno in self.categories[cat] :
                tagstr = self.tag_list[tagno]

                # No empty tags
                if tagstr.strip() == '' :
                    continue

                outstr += "tag %s :" % tagstr
                for img in Image.g_image_list :
                    if tagno in img.tags :
                        outstr += ' ' + img.filename
                outstr += '\n'

        return outstr

    def rename_category(self, old, new) :
        for i in range(len(self.categories)):
            k,v = self.categories.popitem(False)
            self.categories[new if old == k else k] = v

    def write_tag_file(self) :
        '''Save the current set of tags to a Tags file chosen from
           the top-level directory used in the images we've seen.
           If there was a previous Tags file there, it will be saved
           as Tags.bak.
        '''
        if not self.changed :
            print "No tags changed; not rewriting Tags file"
            return

        outpath = os.path.join(self.commondir, "Tags")
        print "Saving to", outpath
        if os.path.exists(outpath) :
            os.rename(outpath, outpath + ".bak")
        outfile = open(outpath, "w")
        outfile.write(str(self))
        outfile.close()

    def read_tags(self, dirname) :
        '''Read in tags from files named in the given directory,
           and tag images in the imagelist appropriately.
           Tags will be appended to the tag_list.
        '''
        # Keep track of the dir common to all directories we use:
        if self.commondir == None :
            self.commondir = dirname
        else :
            self.commondir = os.path.commonprefix([self.commondir, dirname])
                # commonpre has a bug, see
                # http://rosettacode.org/wiki/Find_common_directory_path#Python
                # but this causes other problems:
                # .rpartition(os.path.sep)[0]

        # Might want to be recursive and use os.walk ...
        # or maybe go the other way, search for Tags files
        # *above* the current directory but not below.
        # For now, only take the given directory.
        '''Current format supported:
category Animals
tag squirrels: img_001.jpg img_030.jpg
tag horses: img_042.jpg
tag penguins: img 008.jpg
category Places
tag New Mexico: img_020.jpg img_042.jpg
tag Bruny Island: img 008.jpg
        '''
        self.current_category = "Tags"

        try :
            pathname = os.path.join(dirname, "Tags")
            fp = open(pathname)
            self.tagfiles.append(pathname)
            print "Opened", pathname
        except IOError :
            print "Couldn't find a file named Tags, trying Keywords"
            try :
                pathname = os.path.join(dirname, "Keywords")
                fp = open(pathname)
                self.tagfiles.append(pathname)
            except IOError :
                # Start us off with an empty tag list.
                self.categories[self.current_category] = []
                # print "No Tags file in", dirname
                return

        self.current_category = "Tags"
        for line in fp :
            # The one line type that doesn't need a colon is a cat name.
            if line.startswith('category ') :
                newcat = line[9:].strip()
                if newcat :
                    self.current_category = newcat
                    if self.current_category not in self.categories :
                        self.categories[self.current_category] = []
                else :
                    print "Parse error: couldn't read category name from", line
                continue

            # Any other legal line type must have a colon.
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

            if line.startswith('tagtype ') :
                typename = line[8:colon].strip()

            elif line.startswith('photo ') :
                photoname = line[6:colon].strip()

            else :
                # Anything else is a tag.
                # If it starts with "tag " (as it should), strip that off.
                if line.startswith('tag ') :
                    tagstr = line[4:colon].strip()
                else :
                    tagstr = line[:colon].strip()

                # It may be several comma-separated tags.
                tagnames = map(str.strip, tagstr.split(','))

                for tagname in tagnames :
                    self.process_tag(tagname, objects)

        fp.close()

    def process_tag(self, tagname, filenames) :
        '''After reading a tag from a tags file, add it to the global
           tags list if it isn't there already, and add the given filenames
           to it.
        '''
        try :
            tagindex = self.tag_list.index(tagname)
        except :
            tagindex = len(self.tag_list)
            self.tag_list.append(tagname)

            try :
                self.categories[self.current_category].append(tagindex)
            # KeyError if the key doesn't exist, AttributeError if
            # self.categories[current_category] exists but isn't a list.
            except KeyError :
                self.categories[self.current_category] = [tagindex]

        # Search for images matching the names in filenames
        # XXX pathname issue here: filenames in tag files generally don't
        # have absolute pathnames, so we're only matching basenames and
        # there could be collisions.
        for fil in filenames :
            tagged = False
            for img in Image.g_image_list :
                if img.filename.endswith(fil) and tagindex not in img.tags :
                    img.tags.append(tagindex)
                    tagged = True
                    break
            # Did we find an image matching fil?
            # If not, add it as a non-displayed image.
            if not tagged :
                newim = Image(fil, displayed=False)
                newim.tags.append(tagindex)
                Image.g_image_list.append(newim)

    def add_tag(self, tag, img) :
        '''Add a tag to the given image.
           img is a MetaPho.Image.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index (in the global tags list) of the tag just added,
           or None if error.
        '''
        self.changed = True

        if type(tag) is int :
            if tag not in img.tags :
                img.tags.append(tag)
            return tag

        # Else it's a string. Make a new tag.
        if tag in self.tag_list :
            tagno = self.tag_list.index(tag)
            if tagno not in self.categories[self.current_category] :
                self.categories[self.current_category].append(tagno)
            return

        self.tag_list.append(tag)
        newindex = len(self.tag_list) - 1
        img.tags.append(newindex)
        self.categories[self.current_category].append(newindex)
        return newindex

    def remove_tag(self, tag, img) :
        self.changed = True

        if type(tag) is int :
            if tag in img.tags :
                img.tags.remove(tag)

        # Else it's a string. Remove it if it's there.
        try :
            self.tag_list.remove(tag)
        except :
            pass

    def clear_tags(self, img) :
        img.tags = []

    def toggle_tag(self, tagno, img) :
        '''Toggle tag number tagno for the given img.'''
        self.changed = True

        if tagno in img.tags :
            img.tags.remove(tagno)
            return

        # It's not there yet. See if it exists in the global tag list.
        # if tagno > len(self.tag_list) :
        #     print "Warning: adding a not yet existent tag", tagno

        img.tags.append(tagno)

    def match_tag(self, pattern) :
        '''Return a list of tags matching the pattern.'''
        return None

