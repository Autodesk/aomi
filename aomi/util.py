"""Utilities which are generally that are tied into actual command line
operations processing but do not really fit under seed or render."""
import os
import logging
from aomi.helpers import get_password, path_pieces, \
    backend_type, mount_for_path, abspath
import aomi.validation
import aomi.exceptions
LOG = logging.getLogger(__name__)


def update_user_password(client, userpass):
    """Will update the password for a userpass user"""
    vault_path = ''
    user = ''
    user_path_bits = userpass.split('/')
    if len(user_path_bits) == 1:
        user = user_path_bits[0]
        vault_path = "auth/userpass/users/%s/password" % user
        LOG.debug("Updating password for user %s at the default path", user)
    elif len(user_path_bits) == 2:
        mount = user_path_bits[0]
        user = user_path_bits[1]
        vault_path = "auth/%s/users/%s/password" % (mount, user)
        LOG.debug("Updating password for user %s at path %s", user, mount)
    else:
        client.revoke_self_token()
        raise aomi.exceptions.AomiCommand("invalid user path")

    new_password = get_password()
    obj = {
        'user': user,
        'password': new_password
    }
    client.write(vault_path, **obj)


def update_generic_password(client, path):
    """Will update a single key in a generic secret backend as
    thought it were a password"""
    vault_path, key = path_pieces(path)
    mount = mount_for_path(vault_path, client)
    if not mount:
        client.revoke_self_token()
        raise aomi.exceptions.VaultConstraint('invalid path')

    if backend_type(mount, client) != 'generic':
        client.revoke_self_token()
        raise aomi.exceptions.AomiData("Unsupported backend type")

    LOG.debug("Updating generic password at %s", path)
    existing = client.read(vault_path)
    if not existing or 'data' not in existing:
        LOG.debug("Nothing exists yet at %s!", vault_path)
        existing = {}
    else:
        LOG.debug("Updating %s at %s", key, vault_path)
        existing = existing['data']

    new_password = get_password()
    if key in existing and existing[key] == new_password:
        client.revoke_self_token()
        raise aomi.exceptions.AomiData("Password is same as existing")

    existing[key] = new_password
    client.write(vault_path, **existing)


def password(client, path):
    """Will attempt to contextually update a password in Vault"""
    if path.startswith('user:'):
        update_user_password(client, path[5:])
    else:
        update_generic_password(client, path)


def vault_file(env, default):
    """The path to a misc Vault file
    This function will check for the env override on a file
    path, compute a fully qualified OS appropriate path to
    the desired file and return it if it exists. Otherwise
    returns None
    """
    home = os.environ['HOME'] if 'HOME' in os.environ else \
        os.environ['USERPROFILE']
    filename = os.environ.get(env, os.path.join(home, default))
    filename = abspath(filename)
    if os.path.exists(filename):
        return filename

    return None


def token_file():
    """The path to a Vault Token file"""
    return vault_file('VAULT_TOKEN_FILE', '.vault-token')


def appid_file():
    """The path to an Aomi AppID file"""
    return vault_file('AOMI_APP_FILE', '.aomi-app-token')


def approle_file():
    """The path to an Aomi AppID file"""
    return vault_file('AOMI_APPROLE_FILE', '.aomi-approle')


def vault_time_to_s(time_string):
    """Will convert a time string, as recognized by other Vault
    tooling, into an integer representation of seconds"""
    if not time_string or len(time_string) < 2:
        raise aomi.exceptions \
                  .AomiData("Invalid timestring %s" % time_string)

    last_char = time_string[len(time_string) - 1]
    if last_char == 's':
        return int(time_string[0:len(time_string) - 1])
    elif last_char == 'm':
        cur = int(time_string[0:len(time_string) - 1])
        return cur * 60
    elif last_char == 'h':
        cur = int(time_string[0:len(time_string) - 1])
        return cur * 3600
    elif last_char == 'd':
        cur = int(time_string[0:len(time_string) - 1])
        return cur * 86400
    else:
        raise aomi.exceptions \
            .AomiData("Invalid time scale %s" % last_char)
