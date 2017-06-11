""" Helpers for aomi that are used throughout the application """
from __future__ import print_function
import collections
import tempfile
import itertools as IT
import sys
import os
from base64 import b64encode, b64decode
from random import SystemRandom
from getpass import getpass
from pkg_resources import resource_string, resource_filename
# Python 2/3 compat
from future.utils import iteritems  # pylint: disable=E0401
import aomi.exceptions


def my_version():
    """Return the version, checking both packaged and development locations"""
    if os.path.exists(resource_filename(__name__, 'version')):
        return resource_string(__name__, 'version')

    return open(os.path.join(os.path.dirname(__file__),
                             "..", "version")).read()

VERSION = my_version()


def log(msg, opt):
    """Verbose messaging!"""
    if opt.verbose:
        print(msg, file=sys.stderr)


def warning(msg):
    """Print a warning message to stderr"""
    print("Warning {0}".format(msg), file=sys.stderr)


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


def is_tagged(required_tags, has_tags):
    """Checks if tags match"""
    if not required_tags and not has_tags:
        return True
    elif not required_tags:
        return False

    found_tags = []
    for tag in required_tags:
        if tag in has_tags:
            found_tags.append(tag)

    return len(found_tags) == len(required_tags)


def cli_hash(list_of_kv):
    """Parse out a hash from a list of key=value strings"""
    ev_obj = {}
    for extra_var in list_of_kv:
        ev_list = extra_var.split('=')
        key = ev_list[0]
        val = '='.join(ev_list[1:])  # b64 and other side effects
        ev_obj[key] = val

    return ev_obj


def merge_dicts(dict_a, dict_b):
    """Deep merge of two dicts"""
    obj = {}
    for key, value in iteritems(dict_a):
        if key in dict_b:
            if isinstance(dict_b[key], dict):
                obj[key] = merge_dicts(value, dict_b.pop(key))
        else:
            obj[key] = value

    for key, value in iteritems(dict_b):
        obj[key] = value

    return obj


def get_tty_password(opt, confirm):
    """When returning a password from a TTY we assume a user
    is entering it on a keyboard so we ask for confirmation."""
    log("Reading password from TTY", opt)
    new_password = getpass('Enter Password: ', stream=sys.stderr)
    if not new_password:
        raise aomi.exceptions.AomiCommand("Must specify a password")

    if not confirm:
        return new_password

    confirm_password = getpass('Again, Please: ', stream=sys.stderr)
    if confirm_password != new_password:
        raise aomi.exceptions.AomiCommand("Passwords do not match")

    return new_password


def get_stdin_password(opt):
    """Returns a password from stdin, no confirmation neccesary"""
    log("Reading password from stdin", opt)
    return sys.stdin.readline().rstrip()


def get_password(opt, confirm=True):
    """Will return a password in an appropriate fashion"""
    if sys.stdin.isatty():
        return get_tty_password(opt, confirm)

    return get_stdin_password(opt)


def path_pieces(vault_path):
    """Will return a two part tuple comprising of the vault path
    and the key with in the stored object"""
    path_bits = vault_path.split('/')
    path = '/'.join(path_bits[0:len(path_bits) - 1])
    key = path_bits[len(path_bits) - 1]
    return path, key


def mount_for_path(path, client):
    """Returns the mountpoint for this path"""
    backend_data = client.list_secret_backends()['data']
    backends = [mnt for mnt in backend_data.keys()]
    path_bits = path.split('/')
    if len(path_bits) == 1:
        vault_path = "%s/" % path
        if vault_path in backends:
            return vault_path[0:len(vault_path) - 1]
    else:
        for i in range(1, len(path_bits) + 1):
            vault_path = "%s/" % '/'.join(path_bits[0:i])
            if vault_path in backends:
                return vault_path[0:len(vault_path) - 1]

    return None


def backend_type(path, client):
    """Returns the type of backend at the given mountpoint"""
    backends = client.list_secret_backends()['data']
    vault_path = "%s/" % path
    return backends[vault_path]['type']


def load_word_file(filename):
    """Loads a words file as a list of lines"""
    words_file = resource_filename(__name__, "words/%s" % filename)
    handle = open(words_file, 'r')
    words = handle.readlines()
    handle.close()
    return words


def choose_one(things):
    """Returns a random entry from a list of things"""
    choice = SystemRandom().randint(0, len(things) - 1)
    return things[choice].strip()


def random_word():
    """Returns a random word string"""
    animal = choose_one(load_word_file("animals.txt"))
    academic = choose_one(load_word_file("academic.txt"))
    return "%s-%s" % (academic, animal)


def flatten(iterable):
    """Ensure we are returning an actual list, as that's all we
    are ever going to flatten within aomi"""
    return [x for x in actually_flatten(iterable)]


def actually_flatten(iterable):
    """Flatten iterables"""
    remainder = iter(iterable)
    while True:
        first = next(remainder)
        # Python 2/3 compat
        try:
            basestring
        except NameError:
            # Python 2/3 compat
            basestring = str  # pylint: disable=W0622
        if isinstance(first, collections.Iterable) and \
           not isinstance(first, basestring):
            remainder = IT.chain(first, remainder)
        else:
            yield first


def subdir_path(directory, relative):
    """Returns a file path relative to another path."""
    item_bits = directory.split(os.sep)
    relative_bits = relative.split(os.sep)
    for i in range(0, len(item_bits)):
        if i == len(relative_bits) - 1:
            return os.sep.join(item_bits[i:])
        else:
            if item_bits[i] != relative_bits[i]:
                return None

    return None


def portable_b64encode(thing):
    """Wrap b64encode for Python 2 & 3"""
    if sys.version_info >= (3, 0):
        try:
            some_bits = bytes(thing, 'utf-8')
        except TypeError:
            some_bits = thing

        return b64encode(some_bits).decode('utf-8')

    return b64encode(thing)


def portable_b64decode(thing):
    """Consistent b64decode in Python 2 & 3"""
    if sys.version_info >= (3, 0):
        decoded = b64decode(thing)
        try:
            return decoded.decode('utf-8')
        except UnicodeDecodeError:
            return decoded

    return b64decode(thing)


def open_maybe_binary(filename):
    """Opens something that might be binary but also
    might be "plain text"."""
    if sys.version_info >= (3, 0):
        data = open(filename, 'rb').read()
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data

    return open(filename, 'r').read()


def ensure_dir(path):
    """Ensures a directory exists"""
    if not (os.path.exists(path) and
            os.path.isdir(path)):
        os.mkdir(path)


def ensure_tmpdir():
    """Ensures a temporary directory exists"""
    path = tempfile.mkdtemp('aomi')
    return path
