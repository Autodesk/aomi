"""Some validation helpers for aomi"""
from __future__ import print_function
import os
import re
import platform
import stat
from aomi.helpers import abspath, is_tagged, log, subdir_path
import aomi.exceptions


def find_file(name, directory):
    """Searches up from a directory looking for a file"""
    path_bits = directory.split(os.sep)
    for i in range(0, len(path_bits) - 1):
        check_path = path_bits[0:len(path_bits) - i]
        check_file = "%s%s%s" % (os.sep.join(check_path), os.sep, name)
        if os.path.exists(check_file):
            return abspath(check_file)

    return None


def in_file(string, search_file):
    """Looks in a file for a string."""
    handle = open(search_file, 'r')
    for line in handle.readlines():
        if string in line:
            return True

    return False


def gitignore(opt):
    """Will check directories upwards from the Secretfile in order
    to ensure the gitignore file is set properly"""
    directory = os.path.dirname(abspath(opt.secretfile))
    gitignore_file = find_file('.gitignore', directory)
    if gitignore_file:
        secrets_path = subdir_path(abspath(opt.secrets), gitignore_file)
        if secrets_path:
            if not in_file(secrets_path, gitignore_file):
                e_msg = "The path %s was not found in %s" \
                        % (secrets_path, gitignore_file)
                raise aomi.exceptions.AomiFile(e_msg)
        else:
            log("Using a non-relative secret directory", opt)

    else:
        raise aomi.exceptions.AomiFile("You should really have a .gitignore")


def secret_file(filename):
    """Will check the permissions of things which really
    should be secret files"""
    filestat = os.stat(abspath(filename))
    if stat.S_ISREG(filestat.st_mode) == 0 and \
       stat.S_ISLNK(filestat.st_mode) == 0:
        e_msg = "Secret file %s must be a real file or symlink" % filename
        raise aomi.exceptions.AomiFile(e_msg)

    if platform.system() != "Windows":
        if filestat.st_mode & stat.S_IROTH or \
           filestat.st_mode & stat.S_IWOTH or \
           filestat.st_mode & stat.S_IWGRP:
            e_msg = "Secret file %s has too loose permissions" % filename
            raise aomi.exceptions.AomiFile(e_msg)


def validate_obj(keys, obj):
    """Super simple "object" validation."""
    msg = ''
    for k in keys:
        if isinstance(k, str):
            if k not in obj or (not isinstance(obj[k], list) and not obj[k]):
                if msg:
                    msg = "%s," % msg

                msg = "%s%s" % (msg, k)
        elif isinstance(k, list):
            found = False
            for k_a in k:
                if k_a in obj:
                    found = True

            if not found:
                if msg:
                    msg = "%s," % msg

                msg = "%s(%s" % (msg, ','.join(k))

    if msg:
        msg = "%s missing" % msg

    return msg


def tag_check(obj, path, opt):
    """If we require tags, validate for that"""
    if not is_tagged(opt.tags, obj.get('tags', [])):
        log("Skipping %s as it does not have requested tags" %
            path, opt)
        return False

    return True


def specific_path_check(path, opt):
    """Will make checks against include/exclude to determine if we
    actually care about the path in question."""
    if opt.exclude:
        if path in opt.exclude:
            return False

    if opt.include:
        if path not in opt.include:
            return False

    return True


def check_obj(keys, name, obj):
    """Do basic validation on an object"""
    msg = validate_obj(keys, obj)

    if msg:
        raise aomi.exceptions.AomiData("object check : %s in %s" % (msg, name))


def sanitize_mount(mount):
    """Returns a quote-unquote sanitized mount path"""
    sanitized_mount = mount
    if sanitized_mount.startswith('/'):
        sanitized_mount = sanitized_mount[1:]

    if sanitized_mount.endswith('/'):
        sanitized_mount = sanitized_mount[:-1]

    return sanitized_mount


def gpg_fingerprint(key):
    """Validates a GPG key fingerprint"""
    if len(key) != 8 or not re.match(r'[0-9A-F]{8}', key):
        raise aomi.exceptions.Validation('Invalid GPG Fingerprint')


def is_plain_string(string):
    """Validates we are a plain ol' string"""
    if not string and not re.match(r'[0-9A-Fa-f\-_]', string):
        raise aomi.exceptions.Validation('Not a plain string')
