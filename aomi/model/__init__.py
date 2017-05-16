"""Model definition for various aomi contexts"""

import re
import hvac
import aomi.exceptions
from aomi.helpers import log, is_tagged
from aomi.vault import is_mounted
from aomi.error import output as error_output
from aomi.validation import sanitize_mount, check_obj


def wrap_vault(msg):
    """Error catching Vault API wrapper
    This decorator wraps API interactions with Vault. It will
    catch and return appropriate error output on common
    problems"""
    # pylint: disable=missing-docstring
    def wrap_call(func):
        # pylint: disable=missing-docstring
        def func_wrapper(self, vault_client, opt):
            try:
                return func(self, vault_client, opt)
            except (hvac.exceptions.InvalidRequest,
                    hvac.exceptions.Forbidden) as vault_exception:
                if vault_exception.errors[0] == 'permission denied':
                    error_output("Permission denied %s from %s" %
                                 (msg, self.path), opt)
                else:
                    raise

        return func_wrapper
    return wrap_call


class Resource(object):
    """The base Vault Resource
    All aomi derived Vault resources should extend this
    class. It provides functionality for validation and
    API CRUD operations."""
    required_fields = []
    config_key = None
    resource_key = None
    resource = 'vault resource'
    child = False

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
        to termine just what should be present"""
        if 'tags' in obj and not isinstance(obj['tags'], list):
            raise aomi.exceptions.Validation('tags must be a list')

        if self.present:
            check_obj(self.required_fields, self.resource, obj)

    def __str__(self):
        return "%s %s" % (self.resource, self.path)

    def __init__(self, obj):
        self.grok_state(obj)
        self.validate(obj)
        self.path = None
        self.existing = None
        self.obj = {}
        self.tags = obj.get('tags', [])

    def fetch(self, vault_client, opt):
        """Populate internal representation of remote
        Vault resource contents"""
        result = self.read(vault_client, opt)
        if result:
            if 'data' in result:
                self.existing = result['data']
            else:
                self.existing = result
        else:
            self.existing = None

    def sync(self, vault_client, opt):
        """Update remove Vault resource contents if needed"""
        if self.present and not self.existing:
            log("Writing new data to %s" % self, opt)
            self.write(vault_client, opt)
        elif self.present and self.existing:
            log("Updating data in %s" % self, opt)
            self.write(vault_client, opt)
        elif not self.present and not self.existing:
            log("No data to remove from %s" % self, opt)
        elif not self.present and self.existing:
            log("Removing data from %s" % self, opt)
            self.delete(vault_client, opt)

    def filtered(self, opt):
        """Determines whether or not resource is filtered.
        Resources may be filtered if the tags do not match
        or the user has specified explict paths to include
        or exclude via command line options"""
        if not is_tagged(opt.tags, self.tags):
            log("Skipping %s as it does not have requested tags" %
                self.path, opt)
            return False

        if not aomi.validation.specific_path_check(self.path, opt):
            log("Skipping %s as it does not match specified paths" %
                self.path, opt)
            return False

        return True

    @wrap_vault("reading")
    def read(self, client, opt):
        """Read from Vault while handling non surprising errors."""
        log("Reading from %s" % self, opt)
        return client.read(self.path)

    @wrap_vault("writing")
    def write(self, client, _opt):
        """Write to Vault while handling non-surprising errors."""
        client.write(self.path, **self.obj)

    @wrap_vault("deleting")
    def delete(self, client, opt):
        """Delete from Vault while handling non-surprising errors."""
        log("Deleting %s" % self, opt)
        client.delete(self.path)


class Secret(Resource):
    """Vault Secrets
    These Vault resources will have some kind of secret backend
    underneath them. Seems to work with generic and AWS"""
    config_key = 'secrets'


def filtered_context(context, opt):
    """Filters a context
    This will return a new context with only the resources that
    are actually available for use. Uses tags and command line
    options to make determination."""

    ctx = Context()
    for resource in context.resources():
        if resource.child:
            continue
        if resource.filtered(opt):
            ctx.add(resource)

    return ctx


class Context(object):
    """The overall context of an aomi session"""

    def __init__(self):
        self._mounts = []
        self._resources = []
        self._auths = []
        self._logs = []

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

    def find_backend(self, path, backends):
        for backend in backends:
            if backend.path == path:
                return backend

        return None

    def ensure_backend(self, resource, Backend, backends):
        existing_mount = self.find_backend(resource.mount, backends)
        if not existing_mount:
            new_mount = None
            if Backend == LogBackend:
                new_mount = Backend(resource)
            else:
                new_mount = Backend(resource.mount, resource.backend)

            backends.append(new_mount)
            return new_mount

        return existing_mount

    def add(self, resource):
        if isinstance(resource, Resource):
            if isinstance(resource, (Secret, Mount)):
                self.ensure_backend(resource, SecretBackend, self._mounts)
            elif isinstance(resource, (Auth)):
                self.ensure_backend(resource, AuthBackend, self._auths)
            elif isinstance(resource, (AuditLog)):
                self.ensure_backend(resource, LogBackend, self._logs)

            self._resources.append(resource)
        else:
            msg = "Unknown resource %s being " \
                  "added to context" % resource.__class__
            raise aomi.exceptions.AomiError(msg)

    def uses_mount(self, path):
        rsrcs = []
        for r in self._resources:
            if hasattr(r, 'mount') and r.mount == path:
                rsrcs.append(r)

        return rsrcs

    def remove(self, resource):
        if isinstance(resource, Resource):
            self._resources.remove(resource)

    def sync(self, vault_client, opt):
        for mount in self.mounts():
            if not mount.existing:
                mount.sync(vault_client, opt)
        for auth in self.auths():
            if not auth.existing:
                auth.sync(vault_client, opt)
        for blog in self.logs():
            if not blog.existing:
                blog.sync(vault_client, opt)
        for resource in self.resources():
            resource.sync(vault_client, opt)

    def fetch(self, vault_client, opt):
        for m in self.mounts():
            m.fetch(getattr(vault_client, SecretBackend.list_fun)())
        for a in self.auths():
            a.fetch(getattr(vault_client, AuthBackend.list_fun)())
        for l in self.logs():
            l.fetch(getattr(vault_client, LogBackend.list_fun)())

        for resource in self.resources():
            if issubclass(type(resource), aomi.model.Secret):
                if self.find_backend(resource.mount, self._mounts).existing:
                    resource.fetch(vault_client, opt)
            elif issubclass(type(resource), aomi.model.Auth):
                if self.find_backend(resource.mount, self._auths).existing:
                    resource.fetch(vault_client, opt)
            else:
                resource.fetch(vault_client, opt)


class Auth(Resource):
    def __init__(self, backend, obj):
        super(Auth, self).__init__(obj)
        self.backend = backend

    def backend_exists(self, client):
        """Checks to see if an auth backend exists yet"""
        backends = client.list_auth_backends().keys()
        backends = [x.rstrip('/') for x in backends]
        return self.backend in backends

    def ensure_auth(self, client):
        """Will ensure a particular auth endpoint is mounted"""
        if not self.backend_exists(client):
            client.enable_auth_backend(self.backend)


class Mount(Resource):
    resource = 'Generic Backend'
    required_fields = ['path']
    config_key = 'mounts'
    backend = 'generic'

    def __init__(self, obj, _opt):
        super(Mount, self).__init__(obj)
        self.mount = obj['path']

    def write(self, client, opt):
        pass

    def read(self, client, opt):
        pass

    def delete(self, client, opt):
        pass


class VaultBackend(object):
    backend = None
    list_fun = None
    unmount_fun = None
    mount_fun = None

    @staticmethod
    def list(vault_client, backend_class):
        return getattr(vault_client, backend_class.list_fun)()

    def __str__(self):
        if self.backend == self.path:
            return self.backend

        return "%s %s" % (self.backend, self.path)

    def __init__(self, path, backend):
        self.path = sanitize_mount(path)
        self.backend = backend
        self.existing = False

    def unmount(self, client):
        """Unmount a given mountpoint"""
        backends = getattr(client, self.list_fun)()
        if is_mounted(self.backend, self.path, backends):
            getattr(client, self.unmount_fun)(self.path)

    def sync(self, vault_client, opt):
        """Synchronizes the local and remote Vault resources. Has the net
        effect of adding backend if needed"""
        if not self.existing:
            self.actually_mount(vault_client)
            log("Mounting %s backend on %s" %
                (self.backend, self.path), opt)
        else:
            log("%s backend already mounted on %s" %
                (self.backend, self.path), opt)

    def fetch(self, backends):
        """Updates local resource with context on whether this
        backend is actually mounted and available"""
        self.existing = is_mounted(self.backend, self.path, backends)

    def maybe_mount(self, client, opt):
        """Will ensure a mountpoint exists, or bail with a polite error"""
        backends = getattr(client, self.list_fun)()
        if not is_mounted(self.backend, self.path, backends):
            if self.backend == 'generic':
                log("Specifying a inline generic mountpoint is deprecated",
                    opt)

        self.actually_mount(client)

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
    unmount_fun = 'disable_secret_backend'
    mount_fun = 'enable_secret_backend'


class AuthBackend(VaultBackend):
    """Authentication backends for Vault access"""
    list_fun = 'list_auth_backends'
    unmount_fun = 'disable_auth_backend'
    mount_fun = 'enable_auth_backend'


class LogBackend(VaultBackend):
    """Audit Log backends"""
    list_fun = 'list_audit_backends'
    unmount_fun = 'disable_audit_backend'
    mount_fun = 'enable_audit_backend'

    def __init__(self, resource):
        self.description = None
        super(LogBackend, self).__init__(resource.path, resource.backend)
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
    """Vault Resource for Audit Logging.
    Only supports syslog and file"""
    required_fields = ['type']
    resource = 'Audit Logs'
    config_key = 'audit_logs'

    def write(self, _vault_client, _opt):
        pass

    def __init__(self, log_obj, _opt):
        super(AuditLog, self).__init__(log_obj)
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
