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


def find_unshared_images(dirlist, images_to_check):
    shared = []
    unshared = []

    # Read in the sharefile
    sharedfiles = read_in_sharefile()

    if not images_to_check:
        images_to_check = fotogr.search_for_keywords(dirlist, ['share',
                                                               'wallpaper'],
                                                     [], [],
                                                     True, False)

    for img in images_to_check:
        # print(img)
        datestr = search_in_sharefile(img, sharedfiles)
        if datestr:
            shared.append((datestr, img))
        else:
            unshared.append(img)

    return shared, unshared


def main():
    import argparse
    parser = argparse.ArgumentParser(description="",
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     usage="""%(prog)s: Manage shareable photos.

%(prog)s
    Search in . (or in other directories specified with -d) for photos
    tagged with 'share' that haven't already been shared.

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
        args.dirlist = '.'

    if len(rest) == 1 or rest[1] != 'add':
        # The most common case, do a search
        shared, unshared = find_unshared_images(args.dirlist, rest[1:])
        if not args.quiet:
            for datestr, img in shared:
                print(img, "was shared on", datestr)
            print("unshared images:", end='')
        print(' '.join(unshared))
        sys.exit(0)

    # Add files to the sharefile
    if len(rest) <= 2:
        print("Add what files?")
        sys.exit(1)
    add_to_sharefile(rest[2:])
    sys.exit(0)


if __name__ == '__main__':
    main()
