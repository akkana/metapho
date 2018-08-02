#!/usr/bin/env python2

# Copyright 2013,2016 by Akkana Peck: share and enjoy under the GPL v2 or later.

'''
These are the base class for metapho images and taggers.
Programs with better UI can inherit from these classes.

'''

# Image and Tagger classes have to be defined here in order for
# other files to be able to use them as metapho.Image rather than
# metapho.Image.Image. I haven't found any way that lets me split
# the classes into separate files. Sigh!

import os
import collections    # for OrderedDict

class Image:
    '''An image, with additional info such as rotation and tags.
    '''

    # A list of all the filenames we know about:
    g_image_list = []

    def __init__(self, filename, displayed=True):
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

    def __repr__(self):
        str = "Image '%s'" % self.filename

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
        '''Delete the image file FROM DISK, and the image object
           from the imageList. DOES NOT ASK FOR CONFIRMATION --
           do that (if desired) from the calling program.
        '''
        print "Deleting", self.filename
        os.unlink(self.filename)
        Image.g_image_list.remove(self)

    @classmethod
    def image_index(cls, filename):
        '''Find a name in the global image list. Return index, or None.'''
        for i, img in enumerate(cls.g_image_list):
            if img.filename == filename:
                return i
        return None

    @classmethod
    def find_nonexistent_files(cls):
        '''Returns a list of images in the imagelist that don't exist on disk.
        '''
        not_on_disk = set()
        for im in cls.g_image_list:
            if not os.path.exists(im.filename):
                not_on_disk.add(im.filename)
        not_on_disk = list(not_on_disk)
        not_on_disk.sort()
        return not_on_disk

    @classmethod
    def clean_up_nonexistent_files(cls, topdir):
        '''For any file that was referenced in a tag file but doesn't
           exist on disk, see if perhaps it's been moved to a different
           subdirectory under topdir. If so, adjust file path appropriately.
        '''
        nefbases = set()
        nefdict = {}
        for f in cls.find_nonexistent_files():
            fbase = os.path.basename(f)
            nefbases.add(fbase)
            if fbase in nefdict:
                print "Warning: multiple files named", fbase
            else:
                nefdict[fbase] = f

        for root, dirs, files in os.walk(topdir):
            root = os.path.normpath(root)
            for f in files:
                if f in nefbases:
                    try:
                        i = cls.image_index(nefdict[f])
                        cls.g_image_list[i].filename = os.path.join(root, f)
                    except ValueError:
                        print "Eek!", nefdict[f], \
                            "has vanished from the global image list"

                    nefbases.remove(f)

        # Now we've adjusted paths for any file that's moved.
        # But what about files that have simply been removed?
        # Those are still in nefbases.
        if nefbases:
            print "Removing missing files from Tags file:", \
                ' '.join([nefdict[f] for f in nefbases])
            for f in nefbases:
                Image.g_image_list.remove(nefdict[f])

import shlex

class Tagger(object):
    '''Manages tags for images.
    '''

    def __init__(self):
        '''tagger: an object to manage metapho image tags'''

        # The actual per-image lists of tags live in the Image class.
        # Each image has img.tags, which is a list of tag indices.

        # The category list is a list of lists:
        # [ [ "First category", 3, 5, 11 ] ]
        # means category 0 has the name "First category" and includes
        # tags 3, 5 and 11 from the tag_list.
        self.categories = collections.OrderedDict()

        # The tag list is just a list of all tags we know about (strings).
        # A tag may be in several categories.
        self.tag_list = []

        # Files from which we've read tags (named Tags or Keywords)
        self.tagfiles = []
        # the directory common to them, where we'll try to store tags
        self.commondir = None

        # Have any tags changed during this run?
        # Don't update the Tags file if the user doesn't change anything.
        self.changed = False

        # What category are we currently processing? Default is Tags.
        self.current_category = None

        # All the Tags files we read to initialize.
        # We don't necessarily use this, but callers might want to know.
        self.all_tags_files = []

        # Extensions we explicitly don't handle that might nevertheless
        # be in the same directory as images:
        self.skip_extensions = [ ".cr2", ".xcf",
                                 ".mvi", ".avi", ".mov", ".thm",
                                 ".pto", ".txt", ".wav", ".mp3"
                               ]

    def __repr__(self):
        '''Returns a string summarizing all known images and tags,
           suitable for printing on stdout or pasting into a Tags file.
        '''
        outstr = ''
        for cat in self.categories:
            outstr += '\ncategory ' + cat + '\n\n'

            for tagno in self.categories[cat]:
                tagstr = self.tag_list[tagno]

                # No empty tag strings
                if tagstr.strip() == '':
                    continue

                imgstr = ''
                imglist = []
                for img in Image.g_image_list:
                    if tagno in img.tags:
                        imglist.append(img)

                # Now we have all the images in this category.
                # Sort them alphabetically by name.
                imglist.sort()
                for img in imglist:
                    if ' ' in img.filename:
                        imgstr += ' "' + img.filename + '"'
                    else:
                        imgstr += ' ' + img.filename
                if imgstr:
                    outstr += "tag %s :" % tagstr + imgstr + '\n'

        return outstr

    def rename_category(self, old, new):
        for i in range(len(self.categories)):
            k,v = self.categories.popitem(False)
            self.categories[new if old == k else k] = v

    def write_tag_file(self):
        '''Save the current set of tags to a Tags file chosen from
           the top-level directory used in the images we've seen.
           If there was a previous Tags file there, it will be saved
           as Tags.bak.
        '''
        if not self.changed:
            print "No tags changed; not rewriting Tags file"
            return

        outpath = os.path.join(self.commondir, "Tags")
        print "Saving to", outpath
        if os.path.exists(outpath):
            os.rename(outpath, outpath + ".bak")
        outfile = open(outpath, "w")
        outfile.write(str(self))
        outfile.close()

    def read_tags(self, dirname, recursive=True):
        '''Read in tags from files named in the given directory,
           and tag images in the imagelist appropriately.
           Tags will be appended to the tag_list.
           If recursive is True, we'll also look for
           Tags files in subdirectories.
        '''

        # Handle tag files in subdirectories first.
        # The tag file at the top level will override anything lower,
        # and the top-level tag file is the one we'll overwrite.
        if recursive:
            for root, dirs, files in os.walk(dirname):
                for d in dirs:
                    if not Tagger.ignore_directory(d, root):
                        self.read_tags(os.path.join(root, d), recursive=False)

        # Keep track of the dir common to all directories we use:
        # XXX commondir code is still experimental and untested.
        if self.commondir == None:
            self.commondir = dirname
        else:
            self.commondir = os.path.commonprefix([self.commondir, dirname])
                # commonpre has a bug, see
                # http://rosettacode.org/wiki/Find_common_directory_path#Python
                # but this causes other problems:
                # .rpartition(os.path.sep)[0]

        '''Format of the Tags file:
category Animals
tag squirrels: img_001.jpg img_030.jpg
tag horses: img_042.jpg
tag penguins: img 008.jpg

category Places
tag New Mexico: img_020.jpg img_042.jpg
tag Bruny Island: img 008.jpg
           Extra whitespace is fine; category lines are optional;
           "tag " at beginning of tag lines is optional
           (anything that doesn't start with category, tag,
           tagtype or photo is taken to be a specific tag.
           What are tagtype and photo, you ask? Good question;
           I'm sure there were big plans for them at one time.)
        '''
        # The default category name is Tags.
        if not self.current_category:
            self.current_category = "Tags"
            self.categories[self.current_category] = []

        try:
            pathname = os.path.join(dirname, "Tags")
            fp = open(pathname)
            self.tagfiles.append(pathname)
        except IOError:
            # print "Couldn't find a file named Tags, trying Keywords"
            try:
                pathname = os.path.join(dirname, "Keywords")
                fp = open(pathname)
                self.tagfiles.append(pathname)
            except IOError:
                # print "No Tags or Keywords file in", dirname
                return

        pathname = os.path.normpath(pathname)
        # print "Reading tags from", pathname
        self.all_tags_files.append(pathname)

        for line in fp:
            # The one line type that doesn't need a colon is a cat name.
            if line.startswith('category '):
                newcat = line[9:].strip()
                if newcat:
                    self.current_category = newcat
                    if self.current_category not in self.categories:
                        self.categories[self.current_category] = []
                else:
                    print("%s: Parse error: couldn't read category name, %s"
                          % (pathname, line))
                continue

            # Any other legal line type must have a colon.
            colon = line.find(':')
            if colon < 0:
                continue    # If there's no colon, it's not a legal tag line
            if line.find(':', colon+1) >= 0:
                print("%s : Too many colons -- can't parse!" % (pathname, line))
                continue

            # Now we know we have tagname, typename or photoname.
            # Get the list of objects after the colon.
            # Use shlex to handle quoted and backslashed
            # filenames with embedded spaces.
            try:
                objects = shlex.split(line[colon+1:].strip())
                if dirname != '.':
                    objects = [os.path.normpath(os.path.join(dirname, o))
                               for o in objects]
            except ValueError:
                print pathname, "Couldn't parse:", line
                continue

            if line.startswith('tagtype '):
                typename = line[8:colon].strip()

            elif line.startswith('photo '):
                photoname = line[6:colon].strip()

            else:
                # Anything else is a tag.
                # If it starts with "tag " (as it should), strip that off.
                if line.startswith('tag '):
                    tagstr = line[4:colon].strip()
                else:
                    tagstr = line[:colon].strip()

                # It may be several comma-separated tags.
                tagnames = map(str.strip, tagstr.split(','))

                for tagname in tagnames:
                    self.process_tag(tagname, objects)

        fp.close()

    def process_tag(self, tagname, filenames):
        '''After reading a tag from a tags file, add it to the global
           tags list if it isn't there already, and add the given filenames
           to it.
        '''
        try:
            tagindex = self.tag_list.index(tagname)
        except:
            tagindex = len(self.tag_list)
            self.tag_list.append(tagname)

            try:
                self.categories[self.current_category].append(tagindex)
            # KeyError if the key doesn't exist, AttributeError if
            # self.categories[current_category] exists but isn't a list.
            except KeyError:
                self.categories[self.current_category] = [tagindex]

        # Search for images matching the names in filenames
        # XXX pathname issue here: filenames in tag files generally don't
        # have absolute pathnames, so we're only matching basenames and
        # there could be collisions.
        for fil in filenames:
            tagged = False
            for img in Image.g_image_list:
                if img.filename.endswith(fil) and tagindex not in img.tags:
                    img.tags.append(tagindex)
                    tagged = True
                    break
            # Did we find an image matching fil?
            # If not, add it as a non-displayed image.
            if not tagged:
                newim = Image(fil, displayed=False)
                newim.tags.append(tagindex)
                Image.g_image_list.append(newim)

    def add_tag(self, tag, img):
        '''Add a tag to the given image.
           img is a metapho.Image.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index (in the global tags list) of the tag just added,
           or None if error.
        '''
        self.changed = True

        if type(tag) is int:
            if tag not in img.tags:
                img.tags.append(tag)
            return tag

        # Else it's a string. Make a new tag.
        if tag in self.tag_list:
            tagno = self.tag_list.index(tag)
            if tagno not in self.categories[self.current_category]:
                self.categories[self.current_category].append(tagno)
            img.tags.append(tagno)
            return tagno

        self.tag_list.append(tag)
        newindex = len(self.tag_list) - 1
        img.tags.append(newindex)
        self.categories[self.current_category].append(newindex)
        return newindex

    def remove_tag(self, tag, img):
        self.changed = True

        if type(tag) is int:
            if tag in img.tags:
                img.tags.remove(tag)

        # Else it's a string. Remove it if it's there.
        try:
            self.tag_list.remove(tag)
        except:
            pass

    def clear_tags(self, img):
        img.tags = []

    def toggle_tag(self, tagno, img):
        '''Toggle tag number tagno for the given img.'''
        self.changed = True

        if tagno in img.tags:
            img.tags.remove(tagno)
            return

        # It's not there yet. See if it exists in the global tag list.
        # if tagno > len(self.tag_list):
        #     print "Warning: adding a not yet existent tag", tagno

        img.tags.append(tagno)

    def match_tag(self, pattern):
        '''Return a list of tags matching the pattern.'''
        return None

    def find_untagged_files(self, topdir):
        '''Return a list of untagged files and a list of directories
           in which nothing is tagged, under topdir.
        '''
        untagged_files = []
        untagged_dirs = []
        for root, dirs, files in os.walk(topdir):
            deletes = []
            for d in dirs:
                # Build up a list of ignored directories
                # since we can't delete from dirs while iterating over it.
                if Tagger.ignore_directory(d, root):
                    deletes.append(d)
            for d in deletes:
                dirs.remove(d)

            some_local_tags = False
            local_untagged = []
            nfiles = 0
            for f in files:
                if f.startswith("Tags") or f.startswith("Keywords"):
                    continue

                # Assume all image files will have an extension
                if '.' not in f:
                    continue

                # Filter out file extensions we know we don't handle:
                base, ext = os.path.splitext(f)
                if ext in self.skip_extensions:
                    continue

                # Now we have a file that should be tagged. Is it?
                nfiles += 1
                filepath = os.path.normpath(os.path.join(root, f))
                if filepath not in Image.g_image_list:
                    local_untagged.append(filepath)
                elif not some_local_tags:
                    some_local_tags = True
            if some_local_tags:    # Something was tagged in this root
                untagged_files += local_untagged
            elif nfiles:       # There are files, but nothing was tagged
                # print root, "has no Tags file but has", nfiles, "files"
                untagged_dirs.append(os.path.normpath(root))

        return untagged_files, untagged_dirs

    @classmethod
    def ignore_directory(cls, d, path=None):
        '''Detect directory names that don't need to be indexed separately
           and aren't likely to have a Tags file;
           for instance, those that likely contain copies of what's in
           the parent, or small copies for a web page.
           Also, you can skip tagging by creating a file named NoTags.
        '''
        if d == "html" or d == "web" or d == "bad":
            return True
        if path and os.path.exists(os.path.join(path, d, "NoTags")):
            return True
        return False

    @staticmethod
    def print_files_by_directory(filelist):
        '''Given a list of pathnames, group them by which directory
           they belong to and print them in an organized way.
        '''
        dirdic = {}
        for f in filelist:
            # Split into dirname and basename:
            dn, bn = os.path.split(f)
            if dn in dirdic:
                dirdic[dn].append(bn)
            else:
                dirdic[dn] = [ bn ]

        dirlist = dirdic.keys()
        dirlist.sort()
        for d in dirlist:
            print '  %s:' % d
            print Tagger.split_by_line_length(' '.join(dirdic[d]), 74, '    ')

    @staticmethod
    def split_by_line_length(s, linelen, prefix=''):
        '''Given a long string, split it into lines no longer than linelen,
           with each line optionally prefixed, e.g. with indentation.
           Currently this splits only at spaces, not tabs.
        '''
        ret = ''
        while True:
            if len(s) <= linelen:
                return ret + prefix + s
            lastspace = linelen
            while s[lastspace] != ' ':
                lastspace -= 1
            # s[lastspace] is the last space before linelen.
            # Now go back to the last non-space character.
            pos = lastspace
            while s[pos] == ' ':
                pos -= 1
            ret += prefix + s[:pos+1] + '\n'
            s = s[lastspace + 1:]

def main():
    '''Read tags and report any inconsistencies:
       images in the Tags file that don't exist on disk,
       images on disk that aren't in ./Tags.
    '''
    tagger = Tagger()
    tagger.read_tags('.')

    print

    # This might be interesting information but it's too long a list
    # when evaluating a year's photos.
    # print "Found Tags files in:", ' '.join(tagger.all_tags_files)
    # print

    nef = Image.find_nonexistent_files()
    if nef:
        print "Tagged files that don't exist on disk:", ' '.join(nef)
        print

    utf, utd = tagger.find_untagged_files('.')

    if utd:
        print "Directories that need a Tags file:", ' '.join(utd)
        print

    if utf:
        print "Individual files that aren't tagged:" # , ' '.join(utf)
        tagger.print_files_by_directory(utf)

if __name__ == '__main__':
    main()
