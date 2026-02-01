#!/usr/bin/env python3

# Keeping track of photo sharing, e.g. on mastodon.

# List of images already shared are stored in SHAREFILE
# as YYYY-MM-DD<TAB>img1.jpg img2.jpg ...

# Search directories containing photos are expected to have a Tags
# file (such as those produced by metapho) in which files tagged
# for sharing have the tag "share" or "wallpaper".

# Copyright 2024 by Akkana Peck: share and enjoy under the GPLv2 or later.


from datetime import date
import os, sys

from . import fotogr


SHAREFILE = os.path.expanduser('~/Docs/Lists/sharephotos')


def read_in_sharefile():
    sharedfiles = []
    try:
        with open(SHAREFILE) as fp:
            for line in fp:
                datestr, files = line.strip().split('\t')
                filelist = [ f.strip() for f in files.split() ]
                sharedfiles.append((datestr, filelist))
    except FileNotFoundError:
        print("No sharefile found at", SHAREFILE)

    return sharedfiles


def add_to_sharefile(imglist):
    if not imglist:
        print("empty image list")
        return
    with open(SHAREFILE, 'a') as fp:
        print('%s\t%s' % (date.today().strftime("%Y-%m-%d"),
                          ' '.join(imglist)), file=fp)
        print("Added to the sharefile", SHAREFILE)


def search_in_sharefile(imgname, sharedfiles):
    """The sharefile can have directory fragments, like lassen/img.jpg
       so search for anything that includes namefrag.
       Return the most recent date it was shared, or None if not found.
    """
    namefrag = os.path.basename(imgname)
    most_recent_date = None
    for datestr, filelist in sharedfiles:
        for f in filelist:
            if namefrag in f:
                most_recent_date = datestr
                # print(imgname, "was shared on", datestr,
                #       "because", namefrag, "is in", f)

    return most_recent_date


def find_unshared_images(dirlist, keywords=[]):
    """Find images tagged with 'share' or 'wallpaper' that haven't
       been shared before.
       If keywords is set, look for those instead.
       keywords use the + and - syntax used by fotogr.
    """
    if keywords:
        orpats, andpats, notpats = fotogr.parse_pattern_args(keywords)
    else:
        orpats = ['share', 'wallpaper']
        andpats = []
        notpats = []

    # print("Looking for unshared photos with keywords:", keywords, "in", dirlist)
    images_to_check = fotogr.search_for_keywords(dirlist,
                                                 orpats, andpats, notpats,
                                                 True, False)
    shared, unshared = find_shared_image_times(list(images_to_check))
    return unshared


def find_shared_image_times(images_to_check):
    """Find images that have been either shared or unshared.
       Return a list of (filename, date) for images that have been shared,
       and a list of unshared images.
    """
    shared = []
    unshared = []

    # Read in the sharefile
    sharedfiles = read_in_sharefile()

    for img in images_to_check:
        datestr = search_in_sharefile(img, sharedfiles)
        if datestr:
            shared.append((datestr, img))
        else:
            unshared.append(img)

    # print("shared:")
    # for s in shared:
    #     print("   ", s)
    # print("unshared:")
    # for s in unshared:
    #     print("   ", s)
    return shared, unshared


def main():
    import argparse
    parser = argparse.ArgumentParser(description="",
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     usage="""%(prog)s: Manage shareable photos.

%(prog)s [search] [keyword keyword keyword]
    Search in . (or in other directories specified with -d) for photos
    tagged with 'share' that haven't already been shared.
    "search" is the default command, so it may be omitted.

%(prog)s img2.jpg img.jpg ...
    Check whether the specified images have been shared, and when

%(prog)s add img2.jpg img.jpg ...
    Add the specified images to the share list with today's date
""")
    parser.add_argument('-d', action="store", dest="dirlist",
                        help='Directories to search, comma-separated')
    parser.add_argument('-q', dest="quiet", action="store_true", default=False,
                        help='Quiet: print only the list of images, nothing else')
    args, rest = parser.parse_known_args(sys.argv)

    if not args.dirlist:
        args.dirlist = [ '.' ]

    # rest starts with the program name. Don't need that.
    rest = rest[1:]

    if rest and rest[0] in ['search', 'check', 'add']:
        cmd = rest[0]
        rest = rest[1:]
    else:
        cmd = 'search'

    if cmd == 'search':
        # do a search for unshared images
        unshared = find_unshared_images(args.dirlist, rest)
        print(' '.join(unshared))
        sys.exit(0)

    if cmd == 'check':
        # check status of specified images
        shared, unshared = find_shared_image_times(rest)
        if not args.quiet:
            for datestr, img in shared:
                print(img, "was shared on", datestr)
            print("unshared images: ", ' '.join(unshared))
        sys.exit(0)

    if cmd == 'add':
        # Add files to the sharefile as shared today
        if len(rest) < 1:
            print("Add what files?")
            sys.exit(1)
        add_to_sharefile(rest)
        sys.exit(0)


if __name__ == '__main__':
    main()
