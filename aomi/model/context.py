"""A Context contains a set of Vault resources which may
or may not end up written to the HCV instance. This
context may be filtered, or pre/post processed."""
import sys
import inspect
import logging
from future.utils import iteritems  # pylint: disable=E0401
from aomi.helpers import normalize_vault_path
import aomi.exceptions as aomi_excep
from aomi.model.resource import Resource, Mount, Secret, \
    Auth, AuditLog
from aomi.model.aws import AWS
from aomi.model.auth import Policy, UserPass, LDAP
from aomi.model.backend import LogBackend, AuthBackend, \
    SecretBackend
LOG = logging.getLogger(__name__)


def filtered_context(context):
    """Filters a context
    This will return a new context with only the resources that
    are actually available for use. Uses tags and command line
    options to make determination."""

    ctx = Context(context.opt)
    for resource in context.resources():
        if resource.child:
            continue

        if resource.filtered():
            ctx.add(resource)

    return ctx


def childless_first(resource):
    """Used to sort resources in a way where child resources
    show at the end. This allows us to ensure that required
    dependencies are in place, like with approles"""
    return resource.child


def absent_sort(resource):
    """Used to sort resources in a way where things that
    are being removed are prioritized over things that
    are being added or modified"""
    return resource.present


def find_backend(path, backends):
    """Find the backend at a given path"""
    for backend in backends:
        if backend.path == path:
            return backend

    return None


def ensure_backend(resource, backend, backends, opt):
    """Ensure the backend for a resource is properly in context"""
    existing_mount = find_backend(resource.mount, backends)
    if not existing_mount:
        new_mount = backend(resource, opt)
        backends.append(new_mount)
        return new_mount

    return existing_mount


def find_model(config, obj, mods):
    """Given a list of mods (as returned by py_resources) attempts to
    determine if a given Python obj fits one of the models"""
    for mod in mods:
        if mod[0] != config:
            continue

        if len(mod) == 2:
            return mod[1]

        if len(mod) == 3 and mod[1] in obj:
            return mod[2]

    return None


def py_resources():
    """Discovers all aomi Vault resource models. This includes
    anything extending aomi.model.Mount or aomi.model.Resource."""
    aomi_mods = [m for
                 m, _v in iteritems(sys.modules)
                 if m.startswith('aomi.model')]
    mod_list = []
    mod_map = []
    for amod in [sys.modules[m] for m in aomi_mods]:
        for _mod_bit, model in inspect.getmembers(amod):
            if str(model) in mod_list:
                continue

            if model == Mount:
                mod_list.append(str(model))
                mod_map.append((model.config_key, model))
            elif (inspect.isclass(model) and
                  issubclass(model, Resource) and
                  model.config_key):
                mod_list.append(str(model))
                if model.resource_key:
                    mod_map.append((model.config_key,
                                    model.resource_key,
                                    model))
                elif model.config_key != 'secrets':
                    mod_map.append((model.config_key, model))

    return mod_map


def resource_sort(seed_key):
    """A sorting function based on which resources
    need to be first, in order to ensure that backends
    are properly created."""
    if seed_key == 'mounts' or \
       seed_key == 'userpass' or\
       seed_key == 'audit_logs':
        return False

    return True


class Context(object):
    """The overall context of an aomi session"""

    @staticmethod
    def load(config, opt):
        """Loads and returns a full context object based on the Secretfile"""
        ctx = Context(opt)
        seed_map = py_resources()
        seed_keys = sorted(set([m[0] for m in seed_map]), key=resource_sort)
        for config_key in seed_keys:
            if config_key not in config:
                continue
            for resource_config in config[config_key]:
                mod = find_model(config_key, resource_config, seed_map)
                if not mod:
                    LOG.warning("unable to find mod for %s", resource_config)
                    continue

                ctx.add(mod(resource_config, opt))

        for config_key in config.keys():
            if config_key != 'pgp_keys' and \
               config_key not in seed_keys:
                LOG.warning("missing model for %s", config_key)

        return filtered_context(ctx)

    def thaw(self, tmp_dir):
        """Will thaw every secret into an appropriate temporary location"""
        for resource in self.resources():
            if resource.present:
                resource.thaw(tmp_dir)

    def freeze(self, dest_dir):
        """Freezes every resource within a context"""
        for resource in self.resources():
            if resource.present:
                resource.freeze(dest_dir)

    def __init__(self, opt):
        self._mounts = []
        self._resources = []
        self._auths = []
        self._logs = []
        self.opt = opt

    def mounts(self):
        """Secret backends within context"""
        return self._mounts

    def logs(self):
        """Audit log backends within context"""
        return self._logs

    def auths(self):
        """Authentication backends within context"""
        return self._auths

    def resources(self):
        """Vault resources within context"""
        res = []
        for resource in self._resources:
            res = res + resource.resources()

        return res

    def add(self, resource):
        """Add a resource to the context"""
        if isinstance(resource, Resource):
            if isinstance(resource, (Secret, Mount)) and \
               resource.mount != 'cubbyhole':
                ensure_backend(resource, SecretBackend, self._mounts, self.opt)
            elif isinstance(resource, (Auth)):
                ensure_backend(resource, AuthBackend, self._auths, self.opt)
            elif isinstance(resource, (AuditLog)):
                ensure_backend(resource, LogBackend, self._logs, self.opt)

            self._resources.append(resource)
        else:
            msg = "Unknown resource %s being " \
                  "added to context" % resource.__class__
            raise aomi_excep.AomiError(msg)

    def remove(self, resource):
        """Removes a resource from the context"""
        if isinstance(resource, Resource):
            self._resources.remove(resource)

    def sync_policies(self, vault_client):
        """Synchronizes policies only"""
        p_resources = [x for x in self.resources()
                       if isinstance(x, Policy)]
        for resource in p_resources:
            resource.sync(vault_client)

        return [x for x in self.resources()
                if not isinstance(x, Policy)]

    def sync_auth(self, vault_client, resources):
        """Synchronizes auth mount wrappers. These happen
        early in the cycle, to ensure that user backends
        are proper. They may also be used to set mount
        tuning"""
        for auth in self.auths():
            auth.sync(vault_client)

        auth_resources = [x for x in resources
                          if isinstance(x, (LDAP, UserPass))]
        for resource in auth_resources:
            resource.sync(vault_client)

        return [x for x in resources
                if not isinstance(x, (LDAP, UserPass, AuditLog))]

    def actually_mount(self, vault_client, resource, active_mounts):
        """Handle the actual (potential) mounting of a secret backend.
        This is called in multiple contexts, but the action will always
        be the same. If we were not aware of the mountpoint at the start
        and it has not already been mounted, then mount it."""
        a_mounts = list(active_mounts)
        if isinstance(resource, Secret) and resource.mount == 'cubbyhole':
            return a_mounts

        active_mount = find_backend(resource.mount, active_mounts)
        if not active_mount:
            actual_mount = find_backend(resource.mount, self._mounts)
            a_mounts.append(actual_mount)
            actual_mount.sync(vault_client)

        return a_mounts

    def sync_mounts(self, active_mounts, resources, vault_client):
        """Synchronizes mount points. Removes things before
        adding new."""
        # Create a resource set that is only explicit mounts
        # and sort so removals are first
        mounts = [x for x in resources
                  if isinstance(x, (Mount, AWS))]

        s_resources = sorted(mounts, key=absent_sort)
        # Iterate over explicit mounts only
        for resource in s_resources:
            active_mounts = self.actually_mount(vault_client,
                                                resource,
                                                active_mounts)

        # OK Now iterate over everything but make sure it is clear
        # that ad-hoc mountpoints are deprecated as per
        # https://github.com/Autodesk/aomi/issues/110
        for resource in [x for x in resources
                         if isinstance(x, Secret)]:
            n_mounts = self.actually_mount(vault_client,
                                           resource,
                                           active_mounts)
            if len(n_mounts) != len(active_mounts):
                LOG.warning("Ad-Hoc mount with %s. Please specify"
                            " explicit mountpoints.", resource)

            active_mounts = n_mounts

        return active_mounts, [x for x in resources
                               if not isinstance(x, (Mount))]

    def sync(self, vault_client, opt):
        """Synchronizes the context to the Vault server. This
        has the effect of updating every resource which is
        in the context and has changes pending."""
        active_mounts = []
        for audit_log in self.logs():
            audit_log.sync(vault_client)

        # Handle policies only on the first pass. This allows us
        # to ensure that ACL's are in place prior to actually
        # making any changes.
        not_policies = self.sync_policies(vault_client)
        # Handle auth wrapper resources on the next path. The resources
        # may update a path on their own. They may also provide mount
        # tuning information.
        not_auth = self.sync_auth(vault_client, not_policies)
        # Handle mounts only on the next pass. This allows us to
        # ensure that everything is in order prior to actually
        # provisioning secrets. Note we handle removals before
        # anything else, allowing us to address mount conflicts.
        active_mounts, not_mounts = self.sync_mounts(active_mounts,
                                                     not_auth,
                                                     vault_client)
        # Now handle everything else. If "best practices" are being
        # adhered to then every generic mountpoint should exist by now.
        # We handle "child" resources after the first batch
        sorted_resources = sorted(not_mounts, key=childless_first)
        for resource in sorted_resources:
            resource.sync(vault_client)

        for mount in self.mounts():
            if not find_backend(mount.path, active_mounts):
                mount.unmount(vault_client)

        if opt.remove_unknown:
            self.prune(vault_client)

    def prune(self, vault_client):
        """Will remove any mount point which is not actually defined
        in this context. """
        existing = getattr(vault_client,
                           SecretBackend.list_fun)()['data'].items()
        for mount_name, _values in existing:
            # ignore system paths and cubbyhole
            mount_path = normalize_vault_path(mount_name)
            if mount_path.startswith('sys') or mount_path == 'cubbyhole':
                continue

            exists = [resource.path
                      for resource in self.mounts()
                      if normalize_vault_path(resource.path) == mount_path]

            if not exists:
                LOG.info("removed unknown mount %s", mount_path)
                getattr(vault_client, SecretBackend.unmount_fun)(mount_path)

    def fetch(self, vault_client):
        """Updates the context based on the contents of the Vault
        server. Note that some resources can not be read after
        they have been written to and it is up to those classes
        to handle that case properly."""
        backends = [(self.mounts, SecretBackend),
                    (self.auths, AuthBackend),
                    (self.logs, LogBackend)]
        for b_list, b_class in backends:
            existing = getattr(vault_client, b_class.list_fun)()
            for backend in b_list():
                backend.fetch(vault_client, existing)

        for rsc in self.resources():
            if issubclass(type(rsc), Secret):
                nc_exists = (rsc.mount != 'cubbyhole' and
                             find_backend(rsc.mount, self._mounts).existing)
                if nc_exists or rsc.mount == 'cubbyhole':
                    rsc.fetch(vault_client)
            elif issubclass(type(rsc), Auth):
                if find_backend(rsc.mount, self._auths).existing:
                    rsc.fetch(vault_client)
            elif issubclass(type(rsc), Mount):
                rsc.existing = find_backend(rsc.mount,
                                            self._mounts).existing
            else:
                rsc.fetch(vault_client)

        return self
