"""Model definition for various aomi contexts"""

import re
import hvac
import aomi.exceptions
from aomi.helpers import hard_path, log, \
    warning, merge_dicts, cli_hash, random_word
from aomi.error import output as error_output
from aomi.validation import sanitize_mount


class Context(object):
    """The overall context of an aomi session"""
    mounts = []
    secrets = []

    def __init__(self, client):
        self.client = client


class Auth(object):
    def __init__(self, backend):
        self.backend = backend


    def is_auth_backend(self, client):
        """Checks to see if an auth backend exists yet"""
        backends = client.list_auth_backends().keys()
        backends = [x.rstrip('/') for x in backends]
        return self.backend in backends


    def ensure_auth(self, client):
        """Will ensure a particular auth endpoint is mounted"""
        if not self.is_auth_backend(client):
            client.enable_auth_backend(self.backend)

class Mount(object):
    def __init__(self, path, backend):
        self.path = sanitize_mount(path)
        self.backend = backend

    def unmount(self, client):
        """Unmount a given mountpoint"""
        backends = client.list_secret_backends()
        if self.is_mounted(backends):
            client.disable_secret_backend(self.path)


    def is_mounted(self, backends):
        """Determine whether a backend of a certain type is mounted"""
        for mount_name, values in backends.items():
            b_norm = '/'.join([x for x in mount_name.split('/') if x])
            m_norm = '/'.join([x for x in self.path.split('/') if x])
            if (m_norm == b_norm) and values['type'] == self.backend:
                return True

        return False


    def maybe_mount(self, client, opt):
        """Will ensure a mountpoint exists, or bail with a polite error"""
        backends = client.list_secret_backends()
        if not self.is_mounted(backends):
            if self.backend == 'generic':
                log("Specifying a inline generic mountpoint is deprecated", opt)

        self.actually_mount(client)


    def actually_mount(self, client):
        """Actually mount something in Vault"""
        try:
            client.enable_secret_backend(self.backend, mount_point=self.path)
        except hvac.exceptions.InvalidRequest as exception:
            client.revoke_self_token()
            match = re.match('existing mount at (?P<path>.+)', str(exception))
            if match:
                e_msg = "%s has a mountpoint conflict with %s" % \
                        (self.path, match.group('path'))
                raise aomi.exceptions.VaultConstraint(e_msg)
            else:
                raise exception


class Secret(object):

    def __init__(self, path, backend, varz):
        self.path = path
        self.backend = backend
        self.varz = varz

    def write(self, client, opt):
        """Write to Vault while handling non-surprising errors."""
        try:
            client.write(self.path, **self.varz)
        except (hvac.exceptions.InvalidRequest,
                hvac.exceptions.Forbidden) as vault_exception:
            client.revoke_self_token()
            if vault_exception.errors[0] == 'permission denied':
                error_output("Permission denied writing to %s" % self.path, opt)
            else:
                raise vault_exception


    def delete(self, client, opt):
        """Delete from Vault while handling non-surprising errors."""
        try:
            client.delete(self.path)
        except (hvac.exceptions.InvalidRequest,
                hvac.exceptions.Forbidden) as vault_exception:
            client.revoke_self_token()
            if vault_exception.errors[0] == 'permission denied':
                error_output("Permission denied deleting %s" % self.path, opt)
            else:
                raise vault_exception
           
