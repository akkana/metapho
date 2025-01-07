#!/usr/bin/env python3

# The objects defined in this file are to get around Python's wacky
# and unpredictable lack of true global variables.
# I utterly failed at trying to treat g_cur_imgno imported from metapho.py
# as a global when used in submodules. So instead, here's a singleton
# object that manages the image list and the pointer into it,
# so other classes never need to access the global.


cur_imgno = -1

img_list = []


def current_image():
    try:
        return img_list[cur_imgno]
    except:
        return None

def current_imageno():
    return cur_imgno

def set_current_imageno(val):
    global cur_imgno
    cur_imgno= val

def image_list():
    return img_list

def get_image(imgno):
    return img_list[imgno]

def num_images():
    return len(img_list)

def clear_images():
    # As usual, global doesn't work. But this should:
    img_list.clear()

def num_valid_images():
    return len ([ im for im in img_list if not im.invalid ])

def advance():
    """Increment cur_imgno by 1"""
    global cur_imgno
    cur_imgno += 1

def retreat():
    """Decrement cur_imgno by 1"""
    global cur_imgno
    cur_imgno -= 1

def set_imageno(val):
    global cur_imgno
    cur_imgno = val

def add_images(newlist_or_img):
    """Pass either a list of MetaphoImage or a single MetaphoImage.
    """
    if type(newlist_or_img) is list:
        img_list.extend(newlist_or_img)
    else:
        img_list.append(newlist_or_img)
        # XXX Should make sure it's a MetaphoImage, or create one
        # if it's just a string, but trying to import metapho from here
        # is a circular import so that needs to be solved first.

    # else:
    #     raise TypeError("Can't add_to_image_list with type %s"
    #                     % type(newlist_or_img))

def remove_image(img=None):
    """Remove the indicated image. If img is None, remove the current image."""
    if not img:
        img = current_image()
    img_list.remove(img)

def pop_image(imgno=None):
    if imgno is None:
        imgno = current_imageno()
    return img_list.pop(imgno)
