"""Some validation helpers for aomi"""
from __future__ import print_function
import os
import platform
import stat
from aomi.helpers import problems, abspath, is_tagged, log


def find_file(name, directory):
    """Searches up from a directory looking for a file"""
    path_bits = directory.split(os.sep)
    for i in range(0, len(path_bits) - 1):
        check_path = path_bits[0:len(path_bits) - i]
        check_file = "%s%s%s" % (os.sep.join(check_path), os.sep, name)
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
        secrets_path = subdir_file(abspath(opt.secrets), gitignore_file)
        if not secrets_path:
            problems("Unable to determine relative location of secretfile")

        if not in_file(secrets_path, gitignore_file):
            problems("The path %s was not found in %s" %
                     (secrets_path, gitignore_file))
    else:
        problems("You should really have a .gitignore")


def secret_file(filename):
    """Will check the permissions of things which really
    should be secret files"""
    filestat = os.stat(abspath(filename))
    if stat.S_ISREG(filestat.st_mode) == 0 and \
       stat.S_ISLNK(filestat.st_mode) == 0:
        problems("Secret file %s must be a real file or symlink" % filename)

    if platform.system() != "Windows":
        if filestat.st_mode & stat.S_IROTH or \
           filestat.st_mode & stat.S_IWOTH or \
           filestat.st_mode & stat.S_IWGRP:
            problems("Secret file %s has too loose permissions" % filename)


def validate_obj(keys, obj):
    """Super simple "object" validation."""
    msg = ''
    for k in keys:
        if isinstance(k, str):
            if k not in obj or len(obj[k]) == 0:
                if len(msg) > 0:
                    msg = "%s," % msg

                msg = "%s%s" % (msg, k)
        elif isinstance(k, list):
            found = False
            for k_a in k:
                if k_a in obj:
                    found = True

            if not found:
                if len(msg) > 0:
                    msg = "%s," % msg

                msg = "%s(%s" % (msg, ','.join(k))

    if len(msg) > 0:
        msg = "%s missing" % msg

    return msg


def var_file_obj(obj):
    """Does some validation around a var_file object"""
    check_obj(['var_file', 'mount', 'path'], 'var_file', obj)


def aws_file_obj(obj):
    """Does some validation around an aws_file object"""
    check_obj([['aws_file', 'aws'], 'mount'], 'aws_file', obj)


def aws_secret_obj(filename, obj):
    """Does some validation around AWS secrets"""
    check_obj(['access_key_id', 'secret_access_key'],
              "aws secret %s" % (filename),
              obj)


def aws_role_obj(obj):
    """Does some validation around an AWS role"""
    check_obj(['name'], 'aws role', obj)
    if obj.get('state', 'present') == 'present':
        check_obj([['policy', 'arn'], 'name'], 'aws role', obj)


def file_obj(obj):
    """Basic validation around file objects"""
    check_obj(['mount', 'path'], 'file element', obj)


def tag_check(obj, path, opt):
    """If we require tags, validate for that"""
    if not is_tagged(opt.tags, obj.get('tags', [])):
        log("Skipping %s as it does not have requested tags" %
            path, opt)
        return False
    else:
        return True


def specific_path_check(path, opt):
    """Will make checks against include/exclude to determine if we
    actually care about the path in question."""
    if len(opt.exclude) > 0:
        if path in opt.exclude:
            return False

    if len(opt.include) > 0:
        if path not in opt.include:
            return False

    return True


def check_obj(keys, name, obj):
    """Do basic validation on an object"""
    msg = validate_obj(keys, obj)
    if len(msg) > 0:
        problems("%s in %s" % (msg, name))


def policy_obj(obj):
    """Basic validation around policy objects"""
    state = obj.get('state', 'present')
    if state == 'present':
        check_obj(['name', 'file'], 'policy', obj)
    elif state == 'absent':
        check_obj(['name'], 'policy', obj)
    else:
        problems("Invalid policy state: %s" % state)


def user_obj(obj):
    """Do basic validation on a user obj"""
    check_obj(['username', 'password_file', 'policies'],
              'user specification',
              obj)


def audit_log_obj(obj):
    """Do basic validation on an audit log object"""
    check_obj(['type'], 'audit log object', obj)
    if obj['type'] == 'file':
        check_obj(['file_path'], 'file audit log', obj)


def approle_obj(obj):
    """Do some basic approle validation"""
    check_obj(['name', 'policies'], 'app role', obj)


def generated_obj(obj):
    """Do some basic generated secret validation"""
    check_obj(['mount', 'path', 'keys'], 'generated secret object', obj)
    for key in obj['keys']:
        check_obj(['name', 'method'], 'generated secret entry', key)


def sanitize_mount(mount):
    """Returns a quote-unquote sanitized mount path"""
    sanitized_mount = mount
    if sanitized_mount.startswith('/'):
        sanitized_mount = sanitized_mount[1:]

    if sanitized_mount.endswith('/'):
        sanitized_mount = sanitized_mount[:-1]

    return sanitized_mount


def mount_obj(mount):
    """validates a mountpoint object"""
    check_obj(['path'], 'mount object', mount)


def duo_obj(obj):
    """Validates a duo obj"""
    check_obj(['host', 'creds', 'backend'], 'duo object', obj)
    if obj['backend'] != 'userpass':
        problems('Invalid duo backend selected')
