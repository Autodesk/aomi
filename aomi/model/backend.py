"""Vault Secret Backends"""
import re
import logging
import hvac.exceptions
from aomi.helpers import map_val
from aomi.vault import is_mounted
import aomi.exceptions as aomi_excep
from aomi.validation import sanitize_mount
LOG = logging.getLogger(__name__)
MOUNT_TUNABLES = ['default_lease_ttl', 'max_lease_ttl']

class VaultBackend(object):
    """The abstract concept of a Vault backend"""
    backend = None
    list_fun = None
    mount_fun = None
    unmount_fun = None
    tune_prefix = ""

    def __str__(self):
        if self.backend == self.path:
            return self.backend

        return "%s %s" % (self.backend, self.path)

    def __init__(self, resource, opt):
        self.path = sanitize_mount(resource.mount)
        self.backend = resource.backend
        self.existing = False
        self.present = resource.present
        self.tune = dict()
        if hasattr(resource, 'tune'):
            for tunable in MOUNT_TUNABLES:
                map_val(self.tune, resource.tune, tunable)

        self.opt = opt

    def update_tune(self):
        """Determines if we need to update our tune metadata or not.
        We only do this if we are specifying anything, and it has been
        explicitly set in the data model"""

    def sync(self, vault_client):
        """Synchronizes the local and remote Vault resources. Has the net
        effect of adding backend if needed"""
        if self.present:
            if not self.existing:
                self.actually_mount(vault_client)
                LOG.info("Mounting %s backend on %s",
                         self.backend, self.path)
            elif self.existing:
                LOG.info("%s backend already mounted on %s",
                         self.backend, self.path)

            self.update_tune()
        elif self.existing and not self.present:
            self.unmount(vault_client)
            LOG.info("Unmounting %s backend on %s",
                     self.backend, self.path)
        elif not self.existing and not self.present:
            LOG.info("%s backend already unmounted on %s",
                     self.backend, self.path)

    def sync_tuneables(self, vault_client):
        """Synchtonizes any tunables we have set"""
        if not self.tune:
            return

        a_prefix = self.tune_prefix
        if self.tune_prefix:
            a_prefix = "%s/" % self.tune_prefix

        v_path = "sys/mounts/%s%s/tune" % (a_prefix, self.path)
        t_resp = vault_client.write(v_path, **self.tune())
        if t_resp['errors']:
            raise aomi_excep.VaultData("Unable to update tuning info for %s" % self)

    def fetch(self, vault_client, backends):
        """Updates local resource with context on whether this
        backend is actually mounted and available"""
        self.existing = is_mounted(self.backend, self.path, backends)
        if self.tune_prefix is None:
            return

        a_prefix = self.tune_prefix
        if self.tune_prefix:
            a_prefix = "%s/" % self.tune_prefix

        try:
            t_resp = vault_client.read("sys/mounts/%s%s/tune" % (a_prefix, self.path))
            if 'data' not in t_resp:
                raise aomi_excep.VaultData("Unable to retrieve tuning info for %s" % self)
        except hvac.exceptions.InvalidRequest as vault_excep:
            if 'cannot fetch sysview for path' in vault_excep.errors[0]:
                return

            raise

        self.tune = t_resp['data']

    def unmount(self, client):
        """Unmounts a backend within Vault"""
        getattr(client, self.unmount_fun)(mount_point=self.path)

    def actually_mount(self, client):
        """Actually mount something in Vault"""
        try:
            getattr(client, self.mount_fun)(self.backend,
                                            mount_point=self.path)
        except hvac.exceptions.InvalidRequest as exception:
            match = re.match('existing mount at (?P<path>.+)', str(exception))
            if match:
                e_msg = "%s has a mountpoint conflict with %s" % \
                        (self.path, match.group('path'))
                raise aomi_excep.VaultConstraint(e_msg)
            else:
                raise


class SecretBackend(VaultBackend):
    """Secret Backends for actual Vault resources"""
    list_fun = 'list_secret_backends'
    mount_fun = 'enable_secret_backend'
    unmount_fun = 'disable_secret_backend'


class AuthBackend(VaultBackend):
    """Authentication backends for Vault access"""
    list_fun = 'list_auth_backends'
    mount_fun = 'enable_auth_backend'
    unmount_fun = 'disable_auth_backend'
    tune_prefix = '/auth'

class LogBackend(VaultBackend):
    """Audit Log backends"""
    list_fun = 'list_audit_backends'
    mount_fun = 'enable_audit_backend'
    unmount_fun = 'disable_audit_backend'
    tune_prefix = None

    def __init__(self, resource, opt):
        self.description = None
        super(LogBackend, self).__init__(resource, opt)
        if resource.description:
            self.description = resource.description

        self.obj = resource.obj()

    def actually_mount(self, client):
        if self.description:
            client.enable_audit_backend(self.backend,
                                        name=self.backend,
                                        description=self.description,
                                        options=self.obj)
        else:
            client.enable_audit_backend(self.backend,
                                        name=self.backend,
                                        options=self.obj)

    def unmount(self, client):
        client.disable_audit_backend(self.obj['type'])
