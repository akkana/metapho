#!/usr/bin/env python3

import sys, os

import tkinter as tk
from PIL import Image as PILImage
from PIL import ImageTk, ExifTags, UnidentifiedImageError

from metapho import MetaphoImage


# The numeric key where EXIF orientation is stored.
# None means it hasn't been initialized yet;
# -1 means there was an error initializing, so EXIF orientation won't work.
EXIF_ORIENTATION_KEY = None

VERBOSE = False


class tkPhoImage (MetaphoImage):
    """An image object that saves an original PILImage object
       read in from disk, some state such as rotation,
       possibly a scaled and rotated display PILImage.
       It also knows how to get quantities like size and EXIF rotation.
       And it has tagging attributes since it inherits from MetaphoImage,
       and can be used in the global imagelist.
    """

    INVALID = "Invalid Image"

    def __init__(self, filename):
        MetaphoImage.__init__(self, filename)

        # Rotation of the image as displayed
        self.rot = 0

        # self.rot is initialized by MetaphoImage,
        # but it doesn't handle EXIF
        self.exif_rotation = 0

        # The original image as loaded from the file path.
        # This is never rotated.
        self.orig_img = None

        # Image as currently displayed: rotated and scaled
        self.display_img = None

        # If the image couldn't be loaded, an error string is here:
        errstr = None

    def __repr__(self):
        extra = ''
        if self.orig_img:
            extra += ' orig %dx%d' % self.orig_img.size
        if self.display_img:
            extra += ' displayed %dx%d' % self.display_img.size
        return f'<tkPhoImage {self.relpath}{extra}>'

    # Properties
    def get_size(self):
        if self.display_img:
            return self.display_img.size
        return self.orig_img.size

    size = property(get_size)
    # End Properties

    def load(self):
        """Make sure the image is loaded. May raise FileNotFoundError
           or UnidentifiedImageError.
        """
        # Don't reload if self.orig_img is already there
        if self.orig_img:
            return
        try:
            self.orig_img = PILImage.open(self.relpath)
            self.rot = self.get_exif_rotation()
            self.display_img = None

        except RuntimeError as e:
            self.orig_img = None
            self.display_img = None
            raise e

    def rotate(self, degrees):
        if VERBOSE:
            print("Rotating", degrees, "starting from", self.rot,
                  "-->", self.rot + degrees)
        self.rot = (self.rot + degrees) % 360

        if degrees % 180:
            # If changing aspect ratio, we'll need a new display_img.
            # Clear it, and a new one will be generated by resize_to_fit.
            self.display_img = None

        elif degrees == 180:
            # Rotating without changing aspect ratio:
            # rotate the display_img since size won't change.
            # This could be extra work if we have to do it again.
            # but it could also save work scaling down from the original.
            # XXX Check this.
            if self.display_img:
                self.display_img = self.display_img.rotate(180)
            # self.display_img = None

    def get_exif(self):
        try:
            if not self.orig_img:
                self.load()
            items = self.orig_img._getexif().items()
            exif = {
                ExifTags.TAGS[k]: v
                for k, v in items
                if k in ExifTags.TAGS
            }
            # Decode the GPS info, if any
            gpsinfo = {}
            for key in exif['GPSInfo'].keys():
                decode = ExifTags.GPSTAGS.get(key,key)
                gpsinfo[decode] = exif['GPSInfo'][key]
            if gpsinfo:
                # Now should have 'GPSLatitude', 'GPSLatitudeRef',
                # 'GPSLongitude', 'GPSLongitudeRef'
                # lat/lon are triples like (36.0, 16.0, 12.97)
                # Turn those into more easily read decimal degrees.
                latitude = (float(gpsinfo['GPSLatitude'][0])
                            + float(gpsinfo['GPSLatitude'][1]) / 60.
                            + float(gpsinfo['GPSLatitude'][2]) / 3600.)
                if gpsinfo['GPSLatitudeRef'] == 'S':
                    latitude = -latitude
                longitude = (float(gpsinfo['GPSLongitude'][0])
                    + float(gpsinfo['GPSLongitude'][1]) / 60.
                    + float(gpsinfo['GPSLongitude'][2]) / 3600.)
                if gpsinfo['GPSLongitudeRef'] == 'W':
                    longitude = -longitude
                exif['GPS coordinates'] = '%.6f, %.6f' % (latitude, longitude)
            return exif
        except Exception as e:
            if VERBOSE:
                print("Exception getting exif for", self.relpath,
                      ":", e, file=sys.stderr)
            return {}

    def get_exif_rotation(self):
        global EXIF_ORIENTATION_KEY

        # EXIF_ORIENTATION_KEY is currently 274, but don't count on that.
        if EXIF_ORIENTATION_KEY is None:
            EXIF_ORIENTATION_KEY = -1
            for k in ExifTags.TAGS.keys():
                if ExifTags.TAGS[k] == 'Orientation':
                    EXIF_ORIENTATION_KEY = k
                    break
        if EXIF_ORIENTATION_KEY < 0:
            print("Internal error: can't read any EXIF")
            self.exif_rotation = 0
            return 0

        exif = self.orig_img.getexif()
        try:
            if exif[EXIF_ORIENTATION_KEY] == 3:
                self.exif_rotation = 180
            elif exif[EXIF_ORIENTATION_KEY] == 6:
                self.exif_rotation = -90
            elif exif[EXIF_ORIENTATION_KEY] == 8:
                self.exif_rotation = 90
            if VERBOSE:
                print("EXIF rotation is", self.exif_rotation)
            return self.exif_rotation
        except Exception as e:
            if VERBOSE:
                print("Problem reading EXIF rotation", file=sys.stderr)
            return self.exif_rotation

    def resize_to_fit(self, bbox):
        """Ensure that display_img, as rotated and scaled, fits in the
           bbox (width, height), reloading from orig_img if needed.
           Return self.display_img, a PILImage.
        """
        if not self.orig_img:
            self.load()

        # Is there already a display_image of the correct size?
        # That means one dimension should match the bbox, the other is <=
        if self.display_img:
            dw, dh = self.display_img.size
            if ((dw == bbox[0] and dh <= bbox[1]) or
                (dw <= bbox[0] and dh == bbox[1])):
                if VERBOSE:
                    print("display image is already scaled to the window")
                return self.display_img

        # What are the original dimensions, taking rotation into account?
        # (orig_img is not rotated, display_img is)
        if self.rot % 90:
            oh, ow = self.orig_img.size
        else:
            ow, oh = self.orig_img.size

        # Would the original image fit in the bbox?
        if ow <= bbox[0] and oh <= bbox[1]:
            # It would fit. Is there already a display image that size?
            if self.display_img and self.display_img.size == (ow, oh):
                if VERBOSE:
                    print("display image is already small enough")
                return self.display_img
            # Nope. So create a new display_img, possibly rotated
            if self.rot % 90:
                self.display_img = self.orig_img.rotate(self.rot)
            else:
                self.display_img = self.orig_img
            return self.display_img

        # display_img is bigger than the bbox.
        # Need to scale down from orig_img, which may first involve rotating it
        if self.rot % 180:
            self.display_img = self.orig_img.rotate(self.rot, expand=True)
        elif self.rot:
            self.display_img = self.orig_img.rotate(self.rot, expand=True)
        else:
            self.display_img = self.orig_img

        # Now resize it to fit:
        if VERBOSE:
            print("Resizing to fit in %dx%d" % bbox)
        wratio = self.display_img.size[0] / bbox[0]
        hratio = self.display_img.size[1] / bbox[1]
        ratio = max(wratio, hratio)
        dw, dh = self.display_img.size
        self.display_img = self.display_img.resize(size=(int(dw / ratio),
                                                         int(dh / ratio)))
        if VERBOSE:
            print("Resized to", self.display_img.size)

        return self.display_img

