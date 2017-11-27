""" Helpers for aomi that are used throughout the application """
from __future__ import print_function
import sys
import os
import atexit
import tempfile
import collections
from shutil import rmtree
from random import SystemRandom
from getpass import getpass
import logging
from pkg_resources import resource_string, resource_filename
# Python 2/3 compat
from future.utils import iteritems  # pylint: disable=E0401
import aomi.exceptions
LOG = logging.getLogger(__name__)


def my_version():
    """Return the version, checking both packaged and development locations"""
    if os.path.exists(resource_filename(__name__, 'version')):
        return resource_string(__name__, 'version')

    return open(os.path.join(os.path.dirname(__file__),
                             "..", "version")).read()


VERSION = my_version()


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
    a_path = abspath(path)
    if os.path.exists(relative):
        LOG.debug("using relative path %s (%s)", relative, path)
        return relative

    LOG.debug("using absolute path %s", a_path)
    return a_path


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


def get_tty_password(confirm):
    """When returning a password from a TTY we assume a user
    is entering it on a keyboard so we ask for confirmation."""
    LOG.debug("Reading password from TTY")
    new_password = getpass('Enter Password: ', stream=sys.stderr)
    if not new_password:
        raise aomi.exceptions.AomiCommand("Must specify a password")

    if not confirm:
        return new_password

    confirm_password = getpass('Again, Please: ', stream=sys.stderr)
    if confirm_password != new_password:
        raise aomi.exceptions.AomiCommand("Passwords do not match")

    return new_password


def get_stdin_password():
    """Returns a password from stdin, no confirmation neccesary"""
    LOG.debug("Reading password from stdin")
    return sys.stdin.readline().rstrip()


def get_password(confirm=True):
    """Will return a password in an appropriate fashion"""
    if sys.stdin.isatty():
        return get_tty_password(confirm)

    return get_stdin_password()


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


def clean_tmpdir(path):
    """Invoked atexit, this removes our tmpdir"""
    if os.path.exists(path) and \
       os.path.isdir(path):
        rmtree(path)


def ensure_tmpdir():
    """Ensures a temporary directory exists"""
    path = tempfile.mkdtemp('aomi')
    atexit.register(clean_tmpdir, path)
    return path


def dict_unicodeize(some_dict):
    """Ensure that every string in a dict is properly represented
    by unicode strings"""

    # some python 2/3 compat
    if isinstance(some_dict, ("".__class__, u"".__class__)):
        if sys.version_info >= (3, 0):
            return some_dict

        return some_dict.decode('utf-8')
    elif isinstance(some_dict, collections.Mapping):
        return dict(map(dict_unicodeize, iteritems(some_dict)))
    elif isinstance(some_dict, collections.Iterable):
        return type(some_dict)(map(dict_unicodeize, some_dict))

    return some_dict


def diff_dict(dict1, dict2, ignore_missing=False):
    """Performs a base type comparison between two dicts"""
    unidict1 = dict_unicodeize(dict1)
    unidict2 = dict_unicodeize(dict2)
    if ((not ignore_missing) and (len(unidict1) != len(unidict2))) or \
       (ignore_missing and (len(unidict1) >= len(unidict2))):
        return True

    for comp_k, comp_v in iteritems(unidict1):
        if comp_k not in unidict2:
            return True
        else:
            if comp_v != unidict2[comp_k]:
                return True

    return False


def normalize_vault_path(path):
    """Ensure paths are consistent, always. This covers
    a variety of user specified formats and what HCV
    itself will return in API calls"""
    return '/'.join([x for x in path.split('/') if x])


def map_val(dest, src, key, default=None, src_key=None):
    """Will ensure a dict has values sourced from either
        another dict or based on the provided default"""
    if not src_key:
        src_key = key

    if src_key in src:
        dest[key] = src[src_key]
    else:
        if default is not None:
            dest[key] = default
