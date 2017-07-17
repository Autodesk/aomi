"""Vault Secret Backends"""
import re
import logging
import hvac.exceptions
from aomi.vault import is_mounted
import aomi.exceptions as aomi_excep
from aomi.validation import sanitize_mount
LOG = logging.getLogger(__name__)


class VaultBackend(object):
    """The abstract concept of a Vault backend"""
    backend = None
    list_fun = None
    mount_fun = None
    unmount_fun = None

    @staticmethod
    def list(vault_client, backend_class):
        """List backends"""
        return getattr(vault_client, backend_class.list_fun)()

    def __str__(self):
        if self.backend == self.path:
            return self.backend

        return "%s %s" % (self.backend, self.path)

    def __init__(self, resource, opt):
        self.path = sanitize_mount(resource.mount)
        self.backend = resource.backend
        self.existing = False
        self.present = resource.present
        self.opt = opt

    def sync(self, vault_client):
        """Synchronizes the local and remote Vault resources. Has the net
        effect of adding backend if needed"""
        if not self.existing and self.present:
            self.actually_mount(vault_client)
            LOG.info("Mounting %s backend on %s",
                     self.backend, self.path)
        elif self.existing and self.present:
            LOG.info("%s backend already mounted on %s",
                     self.backend, self.path)
        elif self.existing and not self.present:
            self.unmount(vault_client)
            LOG.info("Unmounting %s backend on %s",
                     self.backend, self.path)
        elif not self.existing and not self.present:
            LOG.info("%s backend already unmounted on %s",
                     self.backend, self.path)

    def fetch(self, backends):
        """Updates local resource with context on whether this
        backend is actually mounted and available"""
        self.existing = is_mounted(self.backend, self.path, backends)

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


class LogBackend(VaultBackend):
    """Audit Log backends"""
    list_fun = 'list_audit_backends'
    mount_fun = 'enable_audit_backend'
    unmount_fun = 'disable_audit_backend'

    def __init__(self, resource, opt):
        self.description = None
        super(LogBackend, self).__init__(resource, opt)
        if resource.description:
            self.description = resource.description

        self.obj = resource.obj

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
