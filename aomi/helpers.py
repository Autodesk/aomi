""" Helpers for aomi that are used throughout the application """
from __future__ import print_function
import sys
import os


def log(msg, opt):
    """Verbose messaging!"""
    if opt.verbose:
        print(msg, file=sys.stderr)


def problems(msg):
    """Simple give-up and error out function."""
    print("Problem: %s" % msg,
          file=sys.stderr)
    exit(1)


def abspath(raw):
    """Return what is hopefully a OS independent path."""
    path_bits = []
    if raw.find('/') != -1:
        path_bits = raw.split('/')
    elif raw.find('\\') != -1:
        path_bits = raw.split('\\')
    else:
        path_bits = [raw]

    return os.path.abspath(os.sep.join(path_bits))


def hard_path(path, prefix_dir):
    """Returns an absolute path to either the relative or absolute file."""
    relative = abspath("%s/%s" % (prefix_dir, path))
    if os.path.exists(relative):
        return relative

    return abspath(path)


def is_tagged(has_tags, required_tags):
    """Checks if tags match"""
    if len(required_tags) == 0:
        return True
    else:
        if len(has_tags) == 0:
            return False
        found_tags = []
        for tag in required_tags:
            if tag in has_tags:
                found_tags.append(tag)

        return len(found_tags) == len(required_tags)
