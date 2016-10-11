""" Helpers for aomi that are used throughout the application """
from __future__ import print_function
import sys
import os
from pkg_resources import resource_string

VERSION = resource_string(__name__, 'version')


def log(msg, opt):
    """Verbose messaging!"""
    if opt.verbose:
        print(msg, file=sys.stderr)


def warning(msg):
    """Print a warning message to stderr"""
    print("Warning {0}".format(msg), file=sys.stderr)


def problems(msg, client=None):
    """Simple give-up and error out function."""
    if client:
        client.revoke_self_token()

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
    if len(required_tags) == 0 and len(has_tags) == 0:
        return True
    elif len(required_tags) == 0:
        return False
    else:
        found_tags = []
        for tag in required_tags:
            if tag in has_tags:
                found_tags.append(tag)

        return len(found_tags) == len(required_tags)


def cli_hash(list_of_kv):
    """Parse out a hash from a list of key=value strings"""
    ev_obj = {}
    for ev in list_of_kv:
        ev_list = ev.split('=')
        key = ev_list[0]
        val = '='.join(ev_list[1:])  # b64 and other side effects
        ev_obj[key] = val

    return ev_obj


def merge_dicts(a, b):
    """Deep merge of two dicts"""
    obj = {}
    for key, value in a.iteritems():
        if key in b:
            if isinstance(b[key], dict):
                obj[key] = merge_dicts(value, b.pop(key))
        else:
            obj[key] = value

    for key, value in b.iteritems():
        obj[key] = value

    return obj
