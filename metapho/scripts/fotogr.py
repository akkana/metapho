#!/usr/bin/env python

# Photo Search:
# Search under the current dir, or the first argument given,
# for grep matches within files named "Keywords".
# Then translate that to a list of full pathnames.
# Copyright 2007,2009,2020,2021 by Akkana Peck:
# share and enjoy under the GPLv2 or later.

# Wish list: Boolean logic. Currently this can search only for one
# term/phrase at a time.

from __future__ import print_function

import glob
import re
import sys, os


DEBUG = False


TAG_FILE_NAMES = ["Tags", "Keywords"]


def search_for_keywords(grepdirs, orpats, andpats, notpats,
                        ignorecase, taglines):
    """Generator: return all files inside the given grepdirs
       which have tags matching the pattern sets.

       Tags are specified in files named Tags or Keywords
       inside any level of the grepdirs.
       Search tag lines looking for matches in the keywords for pats.

       Each item in grepdirs may be a shell-style pattery, like 20??
       (the style used by python's glob module):
       first we'll try to match the item exactly, then if not,
       try to match it as a pattern.
       ~ is allowed.
    """
    if DEBUG:
        print("search_for_keywords", grepdirs)

    if ignorecase:
        orpats = [ p.lower() for p in orpats ]
        andpats = [ p.lower() for p in andpats ]
        notpats = [ p.lower() for p in notpats ]

    for pat in grepdirs:
        for d in glob.glob(os.path.expanduser(pat)):
            for root, dirs, files in os.walk(d):
                if not files:
                    continue
                for tagfilename in TAG_FILE_NAMES:
                    try:
                        for f in search_for_keywords_in(
                                root,
                                os.path.join(root, tagfilename),
                                orpats, andpats, notpats,
                                ignorecase, taglines):
                            yield os.path.normpath(f)

                            # If Tags matched, don't look in Keywords.
                            # If you decide to change this logic,
                            # you'll have to define a set of files
                            # already seen to avoid double reporting.
                        break

                    except FileNotFoundError:
                        # The tags file wasn't there
                        if DEBUG:
                            print("   file not found",
                                  os.path.join(root, tagfilename),
                                  "from", os.getcwd())
                        pass


def search_for_keywords_in(d, f, orpats, andpats, notpats,
                           ignorecase: bool, taglines: bool):
    """Generator:
       Search in d (directory)/f (tagfile) for lines matching or,
       and, and not pats. f is a path to a file named Tags or Keywords,
       and contains lines in a format like:
       [tag ]keyword[, keyword]: file1.jpg [file2.jpg]
       Also treat the directory name as a tag:
       all files match if the patterns match the directory name.
       Yield one matching file at a time.
       taglines: If true, print out tag lines that matched.
    """
    results = []
    filetags = {}
    taglist = []      # only used if taglines is set
    if d.startswith('./'):
        d = d[2:]
    if DEBUG:
        print("Reading tag file", f)

    with open(f) as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            if line.startswith("category "):
                continue
            if line.startswith("tag "):
                line = line[4:]
            # Now we know it's a tag line.
            parts = line.split(':')
            if len(parts) < 2:
                continue
            tags = parts[0].strip()
            if ignorecase:
                tags = tags.lower()
            # There may be several comma-separated tags here, but we
            # actually don't care about that for matching purposes.

            taglist.append(tags)

            for imgfile in parts[1].strip().split():
                filepath = os.path.join(d, imgfile)
                if not os.path.exists(filepath):
                    continue    # Don't match files that no longer exist
                if filepath not in list(filetags.keys()):
                    filetags[filepath] = tags
                else:
                    filetags[filepath] += ', ' + tags

                # Add the name of the directory as a tag.
                # Might want to make this optional at some point:
                # let's see how well it works in practice.
                if d not in filetags[filepath]:
                    filetags[filepath] += ", " + d

    if taglines:
        for tags in taglist:
            if has_match(tags, orpats, andpats, notpats, ignorecase):
                print(d, "has matching tags:", tags)

    # Now we have a list of tagged files in the directory, and their tags.
    for imgfile in list(filetags.keys()):
        tags = filetags[imgfile]
        if DEBUG:
            print(imgfile, ": ", end="")

        if has_match(tags, orpats, andpats, notpats, ignorecase):
            if DEBUG:
                print("*** has a match! yielding", imgfile)
            yield imgfile
        elif DEBUG:
            print("No match, continuing")


def has_match(tags, orpats, andpats, notpats, ignorecase):
    """Do the tags contain any of the patterns in orpats,
       AND all of the patterns in andpats,
       AND none of the patterns in notpats?'
       tags is a string representing all the tags on one file;
       the *pats are lists.
    """
    if DEBUG:
        print("Tags", tags, ": Looking for \n  OR", orpats,
              "\n  AND", andpats, "\n  NOT", notpats)
    if ignorecase:
        flags = re.IGNORECASE
    else:
        flags = 0
    for pat in notpats:
        if pat in tags:
            return False
    for pat in andpats:
        if pat not in tags:
            return False
    if not orpats:
        return True
    for pat in orpats:
        if DEBUG:
            print("re.search '%s', '%s'" % (pat, tags))
        # if pat in tags:
        if re.search(pat, tags, flags):
            return True
    return False

def Usage():
    print('''Usage: %s [-s] [-d dirs] condition [condition ...]

Search for files matching patterns in Tags or Keywords files.
Will search recursively under the current directory unless -d is specified.

Conditions can include three types of patterns:
  1. Starts with +: must be present (AND).
  2. Starts with -: must NOT be present (NOT).
  3. Starts with neither: one of these must be present (OR).

Optional arguments:
  -i              ignore case (this is the default)
  +i              don't ignore case (case is ignored by default)
  -t              taglines: print out the tag lines that match, not just
                  the filenames, in case you need to narrow the search
  -D              show verbose output for debugging
  -d dir,dir,dir  comma-separated list of directories to use (else .)
                  Each dir may be a shell-style pattern, e.g. 19??,20??

Copyright 2009-2022 by Akkana Peck.
Share and enjoy under the GPL v2 or later.''' % os.path.basename(sys.argv[0]))
    sys.exit(0)


def parse_args(args):
    ret = {}

    if not len(args) or args[0] == '-h' or args[0] == '--help':
        Usage()

    # Loop over flag args, which must come before pattern args.
    while True:
        if args[0] == '-i':
            ret["ignorecase"] = True
            args = args[1:]
        elif args[0] == '+i':
            ret["ignorecase"] = False
            args = args[1:]
        elif args[0] == '-t':
            ret["taglines"] = True
            args = args[1:]
        elif args[0] == '-D':
            global DEBUG
            DEBUG = True
            args = args[1:]
        elif args[0].startswith('-d'):
            # -d2019,2020
            if len(args[0]) > 2:
                ret["dirlist"] = args[0][2:].split(',')
                args = args[1:]
                continue
            # -d 2019,2020
            if len(args) == 1:
                Usage()
            ret["dirlist"] = args[1].split(',')
            args = args[2:]
        elif args[0][0] == '-':
            print("Unknown flag", args[0])
            Usage()
        else:
            break

    if "dirlist" not in ret:
        ret["dirlist"] = ['.']
    if "ignorecase" not in ret:
        ret["ignorecase"] = True
    if "taglines" not in ret:
        ret["taglines"] = False

    ret["andpats"] = []
    ret["orpats"]  = []
    ret["notpats"] = []
    for pat in args:
        if pat[0] == '+':
            ret["andpats"].append(pat[1:])
        elif pat[0] == '-':
            ret["notpats"].append(pat[1:])
        else:
            ret["orpats"].append(pat)

    return ret


def main():
    # Sadly, can't use argparse if we want to be able to use -term
    # to indicate "don't search for that term".

    args = parse_args(sys.argv[1:])

    r = search_for_keywords(args["dirlist"],
                            args["orpats"], args["andpats"], args["notpats"],
                            args["ignorecase"], args["taglines"])
    s = set(r)
    r = list(s)
    r.sort()

    if args["taglines"]:
        print()

    for f in r:
        print(f, end=' ')
    print()


if __name__ == "__main__":
    main()


