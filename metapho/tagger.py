#!/usr/bin/env python3

import collections    # for OrderedDict
import shlex
from itertools import takewhile
import re
import sys, os

from . import imagelist
from .metapho import MetaphoImage


# commonprefix is buggy, doesn't restrict itself to path components, see
# http://rosettacode.org/wiki/Find_common_directory_path#Python
# A replacement:
def commonprefix(paths):
    def allnamesequal(name):
        return all(n==name[0] for n in name[1:])

    bydirectorylevels = zip(*[p.split(os.path.sep) for p in paths])
    return os.path.sep.join(x[0] for x in takewhile(allnamesequal,
                                                    bydirectorylevels))


class Tagger(object):
    """Manages tags for images.
    """

    # Extensions we explicitly don't handle that might nevertheless
    # be in the same directory as images:
    try:
        # You can set up your own personal list of extensions to skip
        SKIP_EXTENSIONS = os.getenv("NOTAGS_SKIP_EXTENSIONS").split()
    except:
        SKIP_EXTENSIONS =  [
            ".cr2", ".arw", ".xcf",
            ".mvi", ".avi", ".mov", ".thm", ".mp4", ".mkv",
            ".pto", ".txt", ".wav", ".mp3",
            ".xml", ".pp3"
        ]
    try:
        IGNORE_DIRNAMES = os.getenv("NOTAGS_IGNORE_DIRNAMES").split()
    except:
        IGNORE_DIRNAMES = [ "html", "web", "bad", ".*_assets$" ]

    def __init__(self):
        """tagger: an object to manage metapho image tags"""

        # The actual per-image lists of tags live in the MetaphoImage class.
        # Each image has img.tags, which is a list of tag indices.

        # The category list is an OrderedDict
        # { "First category": [ 3, 5, 11 ] }
        # means category 0 has the name "First category" and includes
        # tags 3, 5 and 11 from the tag_list.
        self.categories = collections.OrderedDict()

        # The tag list is a list of all tags we know about (strings).
        # A tag may be in several categories.
        # The index of a tag in this list is the tag number.
        self.tag_list = []

        # Files from which we've read tags (named Tags or Keywords)
        self.tagfiles = []
        # the directory common to them, where we'll try to store tags
        self.commondir = None

        # Have any tags changed during this run?
        # Don't update the Tags file if the user doesn't change anything.
        self.changed = False

        # What category are we currently processing? Default is Tags.
        self.current_category = ''

        # All the Tags files we read to initialize.
        # We don't necessarily use this, but callers might want to know.
        self.all_tags_files = []

    def __repr__(self):
        """Returns a string summarizing all known images and tags,
           suitable for printing on stdout or pasting into a Tags file.
        """
        outstr = ''
        commondirlen = len(self.commondir)

        for cat in sorted(self.categories):
            outstr += '\ncategory ' + cat + '\n\n'

            # self.categories[cat] is a list of numeric tag indices,
            # so sorting tags would require a lot more code
            # and there's no particular reason to.
            for tagno in self.categories[cat]:
                tagstr = self.tag_list[tagno]

                # No empty tag strings
                if tagstr.strip() == '':
                    continue

                imgstr = ''
                imglist = []
                for img in imagelist.image_list():
                    if tagno in img.tags:
                        imglist.append(img)

                # Now we have all the images in this category.
                # Sort them alphabetically by name.
                imglist.sort()
                for img in imglist:
                    filename = img.filename
                    if filename.startswith(self.commondir):
                        filename = filename[commondirlen+1:]
                    if ' ' in filename:
                        imgstr += ' "' + filename + '"'
                    else:
                        imgstr += ' ' + filename
                if imgstr:
                    outstr += "tag %s :" % tagstr + imgstr + '\n'

        return outstr

    def rename_category(self, old, new):
        for i in range(len(self.categories)):
            k,v = self.categories.popitem(False)
            self.categories[new if old == k else k] = v

    def write_tag_file(self):
        """Save the current set of tags to a Tags file chosen from
           the top-level directory used in the images we've seen.
           If there was a previous Tags file there, it will be saved
           as Tags.bak.
        """
        if not self.changed:
            print("No tags changed; not rewriting Tags file")
            return

        outpath = os.path.join(self.commondir, "Tags")
        print("Saving to", outpath)
        if os.path.exists(outpath):
            os.rename(outpath, outpath + ".bak")
        outfile = open(outpath, "w")
        outfile.write(str(self))
        outfile.close()

    def check_commondir(self, d):
        """Keep track of the dir common to all directories we use:
           XXX commondir code is still somewhat experimental.
        """
        if self.commondir == None:
            self.commondir = d
        else:
            # self.commondir = os.path.commonprefix([self.commondir, d])
            self.commondir = commonprefix([self.commondir, d])

    def read_all_tags_for_images(self):
        """Read tags in all directories used by known images,
           plus the common dir, plus .
        """
        dirs = set()

        for img in imagelist.image_list():
            dirname = os.path.abspath(os.path.dirname(img.filename))
            dirs.add(dirname)

        for d in dirs:
            self.check_commondir(d)

        if not self.commondir:
            print("Yikes! No commondir")

        dirs.add(self.commondir)

        for d in dirs:
            self.read_tags(d, recursive=False)

        MetaphoImage.clean_up_nonexistent_files(self.commondir)

    def read_tags(self, dirname, recursive=True):
        """Read in tags from files named in the given directory,
           and tag images in the imagelist appropriately.
           Tags will be appended to the tag_list.
           If recursive is True, we'll also look for
           Tags files in subdirectories.
        """
        dirname = os.path.abspath(dirname)
        self.check_commondir(dirname)

        # Handle tag files in subdirectories first.
        # The tag file at the top level will override anything lower,
        # and the top-level tag file is the one we'll overwrite.
        if recursive:
            for root, dirs, files in os.walk(dirname):
                for d in dirs:
                    if not Tagger.ignore_directory(d, root):
                        self.read_tags(os.path.join(root, d), recursive=False)

        """Format of the Tags file:
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
           I'm sure there were big plans for them at one time
           but they've never been used.)
        """
        # The default category name is Tags.
        if not self.current_category:
            self.current_category = "Tags"
            self.categories[self.current_category] = []

        try:
            pathname = os.path.join(dirname, "Tags")
            fp = open(pathname)
            self.tagfiles.append(pathname)
        except IOError:
            # print("Couldn't find a file named Tags, trying Keywords")
            try:
                pathname = os.path.join(dirname, "Keywords")
                fp = open(pathname)
                self.tagfiles.append(pathname)
            except IOError:
                # print("No Tags or Keywords file in", dirname)
                return

        pathname = os.path.normpath(pathname)
        # print("Reading tags from", pathname)
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
                    print(("%s: Parse error: couldn't read category name, %s"
                          % (pathname, line)))
                continue

            # Any other legal line type must have a colon.
            # To allow for tags that contain colons, look only for the
            # last one.
            colon = line.rfind(':')
            if colon < 0:
                continue    # If there's no colon, it's not a legal tag line

            # Now we know we have tagname, typename or photoname.
            # Get the list of objects (filenames) after the colon.
            # Use shlex to handle quoted and backslashed
            # filenames with embedded spaces.
            try:
                objects = shlex.split(line[colon+1:].strip())
                if dirname != '.':
                    objects = [os.path.normpath(os.path.join(dirname, o))
                               for o in objects]
            except ValueError:
                print(pathname, "Couldn't parse:", line)
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
                tagnames = list(map(str.strip, tagstr.split(',')))

                for tagname in tagnames:
                    self.process_tag(tagname, objects)

        fp.close()

    def process_tag(self, tagname, filenames):
        """After reading a tag from a tags file, add it to the global
           tags list if it isn't there already, and add the given filenames
           to it.
           filenames are absolute normpaths in atual practice,
           though relpaths aren't prohibited.
        """
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

        # Search for images matching the names in filenames.
        for fil in filenames:
            tagged = False
            for img in imagelist.image_list():
                # if img.filename.endswith(fil) and tagindex not in img.tags:
                if fil.endswith(img.relpath):
                    if tagindex not in img.tags:
                        img.tags.append(tagindex)
                    tagged = True
                    break

            # Did we find an image matching fil?
            # If not, add it as a non-displayed image.
            if not tagged:
                newim = MetaphoImage(fil, displayed=False)
                newim.tags.append(tagindex)
                imagelist.add_images(newim)

    def add_tag(self, tag, img):
        """Add a tag to the given image.
           img is a metapho.MetaphoImage.
           tag may be a string, which can be a new string or an existing one,
           or an integer index into the tag list.
           Return the index (in the global tags list) of the tag just added.
        """
        self.changed = True

        if type(tag) is int:
            if tag not in img.tags:
                img.tags.append(tag)
            return tag

        # Else it's a string. Is it already in the tag list?
        if tag in self.tag_list:
            tagno = self.tag_list.index(tag)
            if tagno not in self.categories[self.current_category]:
                self.categories[self.current_category].append(tagno)
            img.tags.append(tagno)
            return tagno

        # Make a new tag.
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

        # XXX Need to remove it from self.current_category too?

    def change_tag(self, entryno, newstr):
        """Update a tag's string.
           Called on focus_out from one of the text entries (in GUI metapho).
           The entryno should be the same as the index in the current category.
           Changes it for all categories, not just the current one.
        """
        # To change the tag only in the current category,
        # would have to give it a new tag number and resolve the
        # question of whether other images with this tag number
        # want the old or the new string.

        # Number of tags in this category:
        numtags = len(self.categories[self.current_category])

        newstr = newstr.strip()
        if not newstr:
            return
        cur_img = imagelist.current_image()

        try:
            tag_list_no = self.categories[self.current_category][entryno]
        except:
            tag_list_no = None

        # If it's changing an existing tag, just do it.
        if entryno < numtags:
            self.tag_list[self.categories[self.current_category][entryno]] \
                = newstr

        # The string is nonempty and doesn't change an existing tag,
        # so add a new tag.
        else:
            self.add_tag(newstr, cur_img)

        self.changed = True

    def clear_tags(self, img):
        img.tags = []

    def toggle_tag(self, tagno, img):
        """Toggle tag number tagno for the given img."""
        self.changed = True

        if tagno in img.tags:
            img.tags.remove(tagno)
            return

        # It's not there yet. See if it exists in the global tag list.
        # if tagno > len(self.tag_list):
        #     print "Warning: adding a not yet existent tag", tagno

        img.tags.append(tagno)

    def tagname_to_tagno(self, tagname):
        """Given a tag name, return its index in the list. -1 if not found.
        """
        for i, tag in enumerate(self.tag_list):
            if tagname == tag:
                return i
        return -1

    def match_tag(self, pattern):
        """Return a list of tags matching the pattern."""
        print("*** match_tag isn't implemented yet!", file=sys.stderr)
        return None

    def img_has_tags_in(self, img, cat):
        for tag in img.tags:
            if tag in self.categories[cat]:
                return True

    def find_untagged_files(self, topdir):
        """Return a list of untagged files and a list of directories
           in which nothing is tagged, under topdir.
        """
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
                if ext in self.SKIP_EXTENSIONS:
                    continue

                # Now we have a file that should be tagged. Is it?
                nfiles += 1
                filepath = os.path.abspath(os.path.join(root, f))
                if filepath not in imagelist.image_list():
                    local_untagged.append(filepath)
                elif not some_local_tags:
                    some_local_tags = True

            if some_local_tags:    # Something was tagged in this root
                untagged_files += local_untagged
            elif nfiles:       # There are files, but nothing was tagged
                untagged_dirs.append(os.path.abspath(root))

        return untagged_files, untagged_dirs

    @classmethod
    def ignore_directory(cls, d, path=None):
        """Detect directory names that don't need to be indexed separately
           and aren't likely to have a Tags file;
           for instance, those that likely contain copies of what's in
           the parent, or small copies for a web page.
           Also, you can skip tagging by creating a file named NoTags.
        """
        for ipat in Tagger.IGNORE_DIRNAMES:
            if re.match(ipat, d):
                return True
        if path and os.path.exists(os.path.join(path, d, "NoTags")):
            return True
        return False

    @staticmethod
    def print_files_by_directory(filelist):
        """Given a list of pathnames, group them by which directory
           they belong to and print them in an organized way.
        """
        dirdic = {}
        for f in filelist:
            # Split into dirname and basename:
            dn, bn = os.path.split(f)
            if dn in dirdic:
                dirdic[dn].append(bn)
            else:
                dirdic[dn] = [ bn ]

        dirlist = list(dirdic.keys())
        dirlist.sort()
        for d in dirlist:
            if d.strip():
                print('  %s:' % d)

            # Calling split_by_line_length makes for pretty, readable output.
            # However, it's split over multiple lines and thus hard to
            # paste into a metapho command. Might want to make it an option.
            # print(Tagger.split_by_line_length(' '.join(sorted(dirdic[d])), 74, '    '))
            print(' '.join(sorted(dirdic[d])))

    @staticmethod
    def split_by_line_length(s, linelen, prefix=''):
        """Given a long string, split it into lines no longer than linelen,
           with each line optionally prefixed, e.g. with indentation.
           Currently this splits only at spaces, not tabs.
        """
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


def Usage():
    progname = os.path.basename(sys.argv[0])
    print("Usage:", progname)
    print()
    print("""Find directories under the current one that have image files
but lack a file named either Tags or Keywords.""")
    print()
    print(progname, "will ignore files with the following extensions:")
    print('   ', ' '.join(Tagger.SKIP_EXTENSIONS))
    print("    (you can configure that with an environment variable,")
    print("    e.g. export NOTAGS_SKIP_EXTENSIONS='.cr2 .mp3')")
    print(progname, "will ignore directories with these names (regex):")
    print('   ', ' '.join(Tagger.IGNORE_DIRNAMES))
    print("    (configure that with the environment variable "
          "NOTAGS_IGNORE_DIRNAMES)")
    print("    as well as directories with the same name "
          "as the parent directory,\n    e.g. yosemite/yosemite")
    print("It will also ignore any directory containing a file named NoTags.")
    sys.exit(0)


def main():
    """The script linked as notags:
       Read tags and report any inconsistencies:
       images in the Tags file that don't exist on disk,
       images on disk that aren't in ./Tags.
    """
    if len(sys.argv) > 1 and (sys.argv[1] == '-h' or sys.argv[1] == '--help'):
        Usage()

    tagger = Tagger()
    tagger.read_tags('.')

    print()

    curdir = os.path.abspath('.')
    curdirlen = len(curdir)

    def rel_dirs(dirs):
        """Take absolute paths and make them relative to curdir
        """
        # Nested list comprehension, ugh.
        # Remove leading curdir when it exists,
        # but if that results in a null string, substitute '.'.
        return [ d if d else '.'
                 for d in [ p[curdirlen+1:]
                            if p.startswith(curdir)
                            else p for p in dirs ] ]

    # This might be interesting information but it's too long a list
    # when evaluating a year's photos.
    # print "Found Tags files in:", ' '.join(tagger.all_tags_files)
    # print

    nef = MetaphoImage.find_nonexistent_files()
    if nef:
        print("Tagged files that don't exist on disk:", ' '.join(rel_dirs(nef)))
        print()

    utf, utd = tagger.find_untagged_files('.')

    if utd:
        print("Directories that need a Tags file:", ' '.join(rel_dirs(utd)))
        print()

    if utf:
        print("Individual files that aren't tagged:")
        tagger.print_files_by_directory(rel_dirs(utf))


if __name__ == '__main__':
    main()

