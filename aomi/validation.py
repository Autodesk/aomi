"""Some validation helpers for aomi"""
from __future__ import print_function
import os

from aomi.helpers import problems, abspath


def find_file(name, directory):
    """Searches up from a directory looking for a file"""
    path_bits = directory.split(os.sep)
    for i in range(0, len(path_bits) - 1):
        check_path = path_bits[0:len(path_bits) - i]
        check_file = "%s/%s" % (os.sep.join(check_path), name)
        if os.path.exists(check_file):
            return abspath(check_file)

    return None


def subdir_file(item, relative):
    """Returns a file path relative to another file."""
    item_bits = item.split(os.sep)
    relative_bits = relative.split(os.sep)
    for i in range(0, len(item_bits)):
        if i == len(relative_bits) - 1:
            return os.sep.join(item_bits[i:])
        else:
            if item_bits[i] != relative_bits[i]:
                problems("gitignore and secrets paths diverge!")

    return None


def in_file(string, search_file):
    """Looks in a file for a string."""
    h = open(search_file, 'r')
    for l in h.readlines():
        if string in l:
            return True

    return False


def gitignore(opt):
    """Will check directories upwards from the Secretfile in order
    to ensure the gitignore file is set properly"""
    directory = os.path.dirname(abspath(opt.secretfile))
    gitignore_file = find_file('.gitignore', directory)
    if gitignore_file:
        secrets_path = subdir_file(abspath(opt.secrets), gitignore_file)
        if not secrets_path:
            problems("Unable to determine relative location of secretfile")

        if not in_file(secrets_path, gitignore_file):
            problems("The path %s was not found in %s" %
                     (secrets_path, gitignore_file))
    else:
        problems("You should really have a .gitignore")
