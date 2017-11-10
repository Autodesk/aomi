"""Vault Secret Backends"""
import re
import logging
import hvac.exceptions
from aomi.helpers import map_val, diff_dict, normalize_vault_path
from aomi.vault import is_mounted
import aomi.exceptions as aomi_excep
from aomi.validation import sanitize_mount
LOG = logging.getLogger(__name__)
MOUNT_TUNABLES = [
    ('default_lease_ttl', int),
    ('max_lease_ttl', int),
    ('force_no_cache', bool)
]
NOOP = 0
CHANGED = 1
ADD = 2
DEL = 3
OVERWRITE = 4
CONFLICT = 5


class VaultBackend(object):
    """The abstract concept of a Vault backend"""
    backend = None
    list_fun = None
    mount_fun = None
    unmount_fun = None
    tune_prefix = ""
    description = None

    def __str__(self):
        if self.backend == self.path:
            return self.backend

        return "%s %s" % (self.backend, self.path)

    def __init__(self, resource, opt):
        self.path = sanitize_mount(resource.mount)
        self.backend = resource.backend
        self.existing = dict()
        self.present = resource.present
        self.tune = dict()
        self.description = None
        if hasattr(resource, 'tune') and isinstance(resource.tune, dict):
            for tunable in MOUNT_TUNABLES:
                tunable_key = tunable[0]
                tunable_type = tunable[1]
                if tunable_key in resource.tune and \
                   not isinstance(resource.tune[tunable_key], tunable_type):
                    e_msg = "Mount tunable %s on %s must be of type %s" % \
                            (tunable_key, self.path, tunable_type)
                    raise aomi_excep.AomiData(e_msg)

                map_val(self.tune, resource.tune, tunable_key)

            if 'description' in resource.tune:
                self.description = resource.tune['description']

        self.opt = opt

    def update_tune(self):
        """Determines if we need to update our tune metadata or not.
        We only do this if we are specifying anything, and it has been
        explicitly set in the data model"""

    def diff(self):
        """Determines if changes are needed for the Vault backend"""
        if not self.present:
            if self.existing:
                return DEL

            return NOOP

        is_diff = NOOP
        if self.present and self.existing:
            a_obj = self.tune.copy()
            a_obj['description'] = self.description
            if self.tune and diff_dict(a_obj, self.existing, True):
                is_diff = CHANGED

        elif self.present and not self.existing:
            is_diff = ADD

        if self.description != self.existing.get('description'):
            is_diff = CONFLICT

        return is_diff

    def sync(self, vault_client):
        """Synchronizes the local and remote Vault resources. Has the net
        effect of adding backend if needed"""
        if self.present:
            if not self.existing:
                LOG.info("Mounting %s backend on %s",
                         self.backend, self.path)
                self.actually_mount(vault_client)
            else:
                LOG.info("%s backend already mounted on %s",
                         self.backend, self.path)

            self.update_tune()
        else:
            if self.existing:
                LOG.info("Unmounting %s backend on %s",
                         self.backend, self.path)
                self.unmount(vault_client)
            else:
                LOG.info("%s backend already unmounted on %s",
                         self.backend, self.path)

        if self.present and vault_client.version:
            self.sync_tunables(vault_client)

    def sync_tunables(self, vault_client):
        """Synchtonizes any tunables we have set"""
        if not self.tune:
            return

        a_prefix = self.tune_prefix
        if self.tune_prefix:
            a_prefix = "%s/" % self.tune_prefix

        v_path = "sys/mounts/%s%s/tune" % (a_prefix, self.path)
        t_resp = vault_client.write(v_path, **self.tune)
        if t_resp and 'errors' in t_resp and t_resp['errors']:
            e_msg = "Unable to update tuning info for %s" % self
            raise aomi_excep.VaultData(e_msg)

    def fetch(self, vault_client, backends):
        """Updates local resource with context on whether this
        backend is actually mounted and available"""
        if not is_mounted(self.backend, self.path, backends) or \
           self.tune_prefix is None or \
           vault_client.version is None:
            return

        a_prefix = self.tune_prefix
        if self.tune_prefix:
            a_prefix = "%s/" % self.tune_prefix

        v_path = "sys/mounts/%s%s/tune" % (a_prefix, self.path)
        t_resp = vault_client.read(v_path)
        if 'data' not in t_resp:
            e_msg = "Unable to retrieve tuning info for %s" % self
            raise aomi_excep.VaultData(e_msg)

        e_obj = t_resp['data']
        e_obj['description'] = None

        n_path = normalize_vault_path(self.path)
        if n_path in backends:
            a_mount = backends[n_path]
            if 'description' in a_mount and a_mount['description']:
                e_obj['description'] = a_mount['description']

        self.existing = e_obj

    def unmount(self, client):
        """Unmounts a backend within Vault"""
        getattr(client, self.unmount_fun)(mount_point=self.path)

    def actually_mount(self, client):
        """Actually mount something in Vault"""
        try:
            m_fun = getattr(client, self.mount_fun)
            if self.description and self.tune:
                m_fun(self.backend,
                      mount_point=self.path,
                      description=self.description,
                      config=self.tune)
            elif self.description:
                m_fun(self.backend,
                      mount_point=self.path,
                      description=self.description)
            elif self.tune:
                m_fun(self.backend,
                      mount_point=self.path,
                      config=self.tune)
            else:
                m_fun(self.backend,
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

    def actually_mount(self, client):
        m_fun = getattr(client, self.mount_fun)
        if self.description and self.tune:
            m_fun(self.backend,
                  mount_point=self.path,
                  description=self.description)
        elif self.description:
            m_fun(self.backend,
                  mount_point=self.path,
                  description=self.description)
        else:
            m_fun(self.backend,
                  mount_point=self.path)


class LogBackend(VaultBackend):
    """Audit Log backends"""
    list_fun = 'list_audit_backends'
    mount_fun = 'enable_audit_backend'
    unmount_fun = 'disable_audit_backend'
    tune_prefix = None

    def __init__(self, resource, opt):
        super(LogBackend, self).__init__(resource, opt)
        self.obj = resource.obj()

    def actually_mount(self, client):
        client.enable_audit_backend(self.backend, **self.obj)

    def unmount(self, client):
        client.disable_audit_backend(self.backend)
