"""Model definition for various aomi contexts"""
from __future__ import print_function
import sys
import inspect
import os
import re
import shutil
from future.utils import iteritems  # pylint: disable=E0401
import hvac
import aomi.exceptions
from aomi.helpers import log, is_tagged, hard_path
from aomi.vault import is_mounted
from aomi.error import output as error_output
from aomi.validation import sanitize_mount, check_obj


def py_resources():
    """Discovers all aomi Vault resource models"""
    aomi_mods = [m for
                 m, _v in iteritems(sys.modules)
                 if m.startswith('aomi.model')]
    mod_list = []
    mod_map = []
    for amod in [sys.modules[m] for m in aomi_mods]:
        for _mod_bit, model in inspect.getmembers(amod):
            if str(model) in mod_list:
                continue

            if model == aomi.model.Mount:
                mod_list.append(str(model))
                mod_map.append((model.config_key, model))
            elif (inspect.isclass(model) and
                  issubclass(model, aomi.model.Resource) and
                  model.config_key):
                mod_list.append(str(model))
                if model.resource_key:
                    mod_map.append((model.config_key,
                                    model.resource_key,
                                    model))
                elif model.config_key != 'secrets':
                    mod_map.append((model.config_key, model))

    return mod_map


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
        new_mount = None
        if backend == LogBackend:
            new_mount = backend(resource, opt)
        else:
            new_mount = backend(resource.mount, resource.backend, opt)

        backends.append(new_mount)
        return new_mount

    return existing_mount


def wrap_vault(msg):
    """Error catching Vault API wrapper
    This decorator wraps API interactions with Vault. It will
    catch and return appropriate error output on common
    problems"""
    # pylint: disable=missing-docstring
    def wrap_call(func):
        # pylint: disable=missing-docstring
        def func_wrapper(self, vault_client):
            try:
                return func(self, vault_client)
            except (hvac.exceptions.InvalidRequest,
                    hvac.exceptions.Forbidden) as vault_exception:
                if vault_exception.errors[0] == 'permission denied':
                    error_output("Permission denied %s from %s" %
                                 (msg, self.path), self.opt)
                else:
                    raise

        return func_wrapper
    return wrap_call


class Resource(object):
    """Vault Resource
    All aomi derived Vault resources should extend this
    class. It provides functionality for validation and
    API CRUD operations."""
    required_fields = []
    config_key = None
    resource_key = None
    child = False
    secret_format = 'data'

    def thaw(self, tmp_dir):
        """Will perform some validation and copy a
        decrypted secret to it's final location"""
        for sfile in self.secrets():
            src_file = "%s/%s" % (tmp_dir, sfile)
            if not os.path.exists(src_file):
                raise aomi \
                    .exceptions \
                    .IceFile("%s secret missing from icefile" %
                             (self))

            dest_file = "%s/%s" % (self.opt.secrets, sfile)
            dest_dir = os.path.dirname(dest_file)
            if not os.path.exists(dest_dir):
                os.mkdir(dest_dir)

            shutil.copy(src_file, dest_file)
            log("Thawed %s %s" % (self, sfile), self.opt)

    def freeze(self, tmp_dir):
        """Copies a secret into a particular location"""
        for sfile in self.secrets():
            src_file = hard_path(sfile, self.opt.secrets)
            if not os.path.exists(src_file):
                raise aomi.exceptions.IceFile("%s secret not found at %s" %
                                              (self, src_file))

            dest_file = "%s/%s" % (tmp_dir, sfile)
            dest_dir = os.path.dirname(dest_file)
            if not os.path.isdir(dest_dir):
                os.mkdir(dest_dir, 0o700)

            shutil.copy(src_file, dest_file)
            log("Froze %s %s" % (self, sfile), self.opt)

    def resources(self):
        """List of included resources"""
        return [self]

    def grok_state(self, obj):
        """Determine the desired state of this
        resource based on data present"""
        if 'state' in obj:
            my_state = obj['state'].lower()
            if my_state != 'absent' and my_state != 'present':
                raise aomi \
                    .exceptions \
                    .Validation('state must be either "absent" or "present"')

        self.present = obj.get('state', 'present').lower() == 'present'

    def validate(self, obj):
        """Base validation method. Will inspect class attributes
        to dermine just what should be present"""
        if 'tags' in obj and not isinstance(obj['tags'], list):
            raise aomi.exceptions.Validation('tags must be a list')

        if self.present:
            check_obj(self.required_fields, self.name(), obj)

    def name(self):
        """A Friendly Name for our Resource"""
        return self.__doc__.split('\n')[0]

    def __str__(self):
        return "%s %s" % (self.name(), self.path)

    def obj(self):
        """Returns the Python dict/JSON object representation
        of this Secret as it is to be written to Vault"""
        return self._obj

    # note that this is going to be implemented by subclasses
    def secrets(self):  # pylint: disable=no-self-use
        """Returns a list of secrets which may be used used
        locally by this Vault resource"""
        return []

    def __init__(self, obj, opt):
        self.grok_state(obj)
        self.validate(obj)
        self.path = None
        self.existing = None
        self._obj = {}
        self.tags = obj.get('tags', [])
        self.opt = opt

    def fetch(self, vault_client):
        """Populate internal representation of remote
        Vault resource contents"""
        result = self.read(vault_client)
        if result:
            if isinstance(result, dict) and 'data' in result:
                self.existing = result['data']
            else:
                self.existing = result
        else:
            self.existing = None

    def sync(self, vault_client):
        """Update remove Vault resource contents if needed"""
        if self.present and not self.existing:
            log("Writing new %s to %s" %
                (self.secret_format, self), self.opt)
            self.write(vault_client)
        elif self.present and self.existing:
            log("Updating %s in %s" %
                (self.secret_format, self), self.opt)
            self.write(vault_client)
        elif not self.present and not self.existing:
            log("No %s to remove from %s" %
                (self.secret_format, self), self.opt)
        elif not self.present and self.existing:
            log("Removing %s from %s" %
                (self.secret_format, self), self.opt)
            self.delete(vault_client)

    def filtered(self):
        """Determines whether or not resource is filtered.
        Resources may be filtered if the tags do not match
        or the user has specified explict paths to include
        or exclude via command line options"""
        if not is_tagged(self.tags, self.opt.tags):
            log("Skipping %s as it does not have requested tags" %
                self.path, self.opt)
            return False

        if not aomi.validation.specific_path_check(self.path, self.opt):
            log("Skipping %s as it does not match specified paths" %
                self.path, self.opt)
            return False

        return True

    @wrap_vault("reading")
    def read(self, client):
        """Read from Vault while handling non surprising errors."""
        log("Reading from %s" % self, self.opt)
        return client.read(self.path)

    @wrap_vault("writing")
    def write(self, client):
        """Write to Vault while handling non-surprising errors."""
        client.write(self.path, **self.obj())

    @wrap_vault("deleting")
    def delete(self, client):
        """Delete from Vault while handling non-surprising errors."""
        log("Deleting %s" % self, self.opt)
        client.delete(self.path)


class Secret(Resource):
    """Vault Secrets
    These Vault resources will have some kind of secret backend
    underneath them. Seems to work with generic and AWS"""
    config_key = 'secrets'


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


class Context(object):
    """The overall context of an aomi session"""

    @staticmethod
    def load(config, opt):
        """Loads and returns a full context object based on the Secretfile"""
        ctx = Context(opt)
        seed_map = py_resources()
        seed_keys = set([m[0] for m in seed_map])
        for config_key in seed_keys:
            if config_key not in config:
                continue
            for resource in config[config_key]:
                mod = find_model(config_key, resource, seed_map)
                if not mod:
                    print("unable to find mod for %s" % resource)
                    continue

                ctx.add(mod(resource, opt))

        for config_key in config.keys():
            if config_key != 'pgp_keys' and \
               config_key not in seed_keys:
                print("missing model for %s" % config_key)

        f_ctx = aomi.model.filtered_context(ctx)
        return f_ctx

    def thaw(self, tmp_dir):
        """Will thaw a secret into an appropriate location"""
        for resource in self.resources():
            if resource.present:
                resource.thaw(tmp_dir)

    def freeze(self, dest_dir):
        """Freezes everyt resource within a context"""
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
            if isinstance(resource, (Secret, Mount)):
                ensure_backend(resource, SecretBackend, self._mounts, self.opt)
            elif isinstance(resource, (Auth)):
                ensure_backend(resource, AuthBackend, self._auths, self.opt)
            elif isinstance(resource, (AuditLog)):
                ensure_backend(resource, LogBackend, self._logs, self.opt)

            self._resources.append(resource)
        else:
            msg = "Unknown resource %s being " \
                  "added to context" % resource.__class__
            raise aomi.exceptions.AomiError(msg)

    def remove(self, resource):
        """Removes a resource from the context"""
        if isinstance(resource, Resource):
            self._resources.remove(resource)

    def sync(self, vault_client):
        """Synchronizes the context to the Vault server. This
        has the effect of updating every resource which is
        in the context."""
        active_mounts = []
        for mount in self.mounts():
            if not mount.existing:
                mount.sync(vault_client)
        for auth in self.auths():
            if not auth.existing:
                auth.sync(vault_client)
        for blog in self.logs():
            if not blog.existing:
                blog.sync(vault_client)
        for resource in self.resources():
            if isinstance(resource, (Secret, Mount)) and resource.present:
                active_mount = find_backend(resource.mount, active_mounts)
                if not active_mount:
                    actual_mount = find_backend(resource.mount, self._mounts)
                    if actual_mount:
                        active_mounts.append(actual_mount)

            resource.sync(vault_client)

        for mount in self.mounts():
            if not find_backend(mount.path, active_mounts):
                mount.unmount(vault_client)

    def fetch(self, vault_client):
        """Updates the context based on the contents of the Vault
        server. Note that some resources can not be read after
        they have been written to and it is up to those classes
        to handle that case properly."""
        backends = [(self.mounts, SecretBackend),
                    (self.auths, AuthBackend),
                    (self.logs, LogBackend)]
        for b_list, b_class in backends:
            for resource in b_list():
                resource.fetch(getattr(vault_client, b_class.list_fun)())

        for resource in self.resources():
            if issubclass(type(resource), aomi.model.Secret):
                if find_backend(resource.mount, self._mounts).existing:
                    resource.fetch(vault_client)
            elif issubclass(type(resource), aomi.model.Auth):
                if find_backend(resource.mount, self._auths).existing:
                    resource.fetch(vault_client)
            else:
                resource.fetch(vault_client)


class Auth(Resource):
    """Auth Backend"""
    def __init__(self, backend, obj, opt):
        super(Auth, self).__init__(obj, opt)
        self.backend = backend


class Mount(Resource):
    """Vault Generic Backend"""
    required_fields = ['path']
    config_key = 'mounts'
    backend = 'generic'

    def __init__(self, obj, opt):
        super(Mount, self).__init__(obj, opt)
        self.mount = obj['path']
        self.path = self.mount

    def write(self, client):
        return

    def read(self, client):
        return

    def delete(self, client):
        return


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

    def __init__(self, path, backend, opt):
        self.path = sanitize_mount(path)
        self.backend = backend
        self.existing = False
        self.opt = opt

    def sync(self, vault_client):
        """Synchronizes the local and remote Vault resources. Has the net
        effect of adding backend if needed"""
        if not self.existing:
            self.actually_mount(vault_client)
            log("Mounting %s backend on %s" %
                (self.backend, self.path), self.opt)
        else:
            log("%s backend already mounted on %s" %
                (self.backend, self.path), self.opt)

    def fetch(self, backends):
        """Updates local resource with context on whether this
        backend is actually mounted and available"""
        self.existing = is_mounted(self.backend, self.path, backends)

    def unmount(self, client):
        """Unmounts a backend within Vault"""
        log("Unmounting %s backend from %s" %
            (self.backend, self.path), self.opt)
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
                raise aomi.exceptions.VaultConstraint(e_msg)
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
        super(LogBackend, self).__init__(resource.path, resource.backend, opt)
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


class AuditLog(Resource):
    """Audit Logs
    Only supports syslog and file backends"""
    required_fields = ['type']
    config_key = 'audit_logs'

    def write(self, _vault_client):
        pass

    def __init__(self, log_obj, opt):
        super(AuditLog, self).__init__(log_obj, opt)
        self.backend = log_obj['type']
        self.mount = self.backend
        self.description = None
        self.path = log_obj.get('path', self.backend)
        obj = {
            'type': log_obj['type']
        }
        if self.backend == 'file':
            obj['file_path'] = log_obj['file_path']

        if self.backend == 'syslog':
            if 'tag' in log_obj:
                obj['tag'] = log_obj['tag']

            if 'facility' in log_obj:
                obj['facility'] = log_obj['facility']

        if 'description' in obj:
            self.description = obj['description']

        self.obj = obj
