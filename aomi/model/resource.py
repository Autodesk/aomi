"""Base Vault Resources"""
import os
import shutil
import logging
import yaml
import hvac.exceptions
from aomi.util import vault_time_to_s
from aomi.vault import wrap_hvac as wrap_vault
from aomi.helpers import is_tagged, hard_path, diff_dict, map_val, \
    open_maybe_binary
from aomi.model.backend import MOUNT_TUNABLES, NOOP, CHANGED, ADD, \
    DEL, OVERWRITE
import aomi.exceptions as aomi_excep
from aomi.validation import check_obj, specific_path_check, is_unicode, \
    is_vault_time, secret_file
LOG = logging.getLogger(__name__)


class Resource(object):
    """Vault Resource
    All aomi derived Vault resources should extend this
    class. It provides functionality for validation and
    API CRUD operations."""
    required_fields = []
    config_key = None
    resource_key = None
    child = False
    no_resource = False
    secret_format = 'data'

    def thaw(self, tmp_dir):
        """Will perform some validation and copy a
        decrypted secret to it's final location"""
        for sfile in self.secrets():
            src_file = "%s/%s" % (tmp_dir, sfile)
            err_msg = "%s secret missing from icefile" % (self)
            if not os.path.exists(src_file):
                if hasattr(self.opt, 'ignore_missing') and \
                   self.opt.ignore_missing:
                    LOG.warning(err_msg)
                    continue
                else:
                    raise aomi_excep.IceFile(err_msg)

            dest_file = "%s/%s" % (self.opt.secrets, sfile)
            dest_dir = os.path.dirname(dest_file)
            if not os.path.exists(dest_dir):
                os.mkdir(dest_dir)

            shutil.copy(src_file, dest_file)
            LOG.debug("Thawed %s %s", self, sfile)

    def tunable(self, obj):
        """A tunable resource maps against a backend..."""
        self.tune = dict()
        if 'tune' in obj:
            for tunable in MOUNT_TUNABLES:
                tunable_key = tunable[0]
                map_val(self.tune, obj['tune'], tunable_key)
                if tunable_key in self.tune and \
                   is_vault_time(self.tune[tunable_key]):
                    vault_time_s = vault_time_to_s(self.tune[tunable_key])
                    self.tune[tunable_key] = vault_time_s

        if 'description'in obj:
            self.tune['description'] = obj['description']

    def export_handle(self, directory):
        """Get a filehandle for exporting"""
        filename = getattr(self, 'filename')
        dest_file = "%s/%s" % (directory, filename)
        dest_dir = os.path.dirname(dest_file)
        if not os.path.isdir(dest_dir):
            os.mkdir(dest_dir, 0o700)

        return open(dest_file, 'w')

    def export(self, directory):
        """Export exportable resources decoding as needed"""
        if not self.existing or not hasattr(self, 'filename'):
            return

        secret_h = self.export_handle(directory)
        obj = self.existing
        if isinstance(obj, str):
            secret_h.write(obj)
        elif isinstance(obj, dict):
            secret_h.write(yaml.safe_dump(obj))

    def freeze(self, tmp_dir):
        """Copies a secret into a particular location"""
        for sfile in self.secrets():
            src_file = hard_path(sfile, self.opt.secrets)
            if not os.path.exists(src_file):
                raise aomi_excep.IceFile("%s secret not found at %s" %
                                         (self, src_file))

            dest_file = "%s/%s" % (tmp_dir, sfile)
            dest_dir = os.path.dirname(dest_file)
            if not os.path.isdir(dest_dir):
                os.mkdir(dest_dir, 0o700)

            shutil.copy(src_file, dest_file)
            LOG.debug("Froze %s %s", self, sfile)

    def resources(self):
        """List of included resources"""
        return [self]

    def grok_state(self, obj):
        """Determine the desired state of this
        resource based on data present"""
        if 'state' in obj:
            my_state = obj['state'].lower()
            if my_state != 'absent' and my_state != 'present':
                raise aomi_excep \
                    .Validation('state must be either "absent" or "present"')

        self.present = obj.get('state', 'present').lower() == 'present'

    def validate(self, obj):
        """Base validation method. Will inspect class attributes
        to dermine just what should be present"""
        if 'tags' in obj and not isinstance(obj['tags'], list):
            raise aomi_excep.Validation('tags must be a list')

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
        self.tune = None

    def diff(self, obj=None):
        """Determine if something has changed or not"""
        if self.no_resource:
            return NOOP

        if not self.present:
            if self.existing:
                return DEL

            return NOOP

        if not obj:
            obj = self.obj()

        is_diff = NOOP
        if self.present and self.existing:
            if isinstance(self.existing, dict):
                current = dict(self.existing)
                if 'refresh_interval' in current:
                    del current['refresh_interval']

                if diff_dict(current, obj):
                    is_diff = CHANGED
            elif is_unicode(self.existing):
                if self.existing != obj:
                    is_diff = CHANGED

        elif self.present and not self.existing:
            is_diff = ADD

        return is_diff

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
            LOG.info("Writing new %s to %s",
                     self.secret_format, self)
            self.write(vault_client)
        elif self.present and self.existing:
            if self.diff() == CHANGED or self.diff() == OVERWRITE:
                LOG.info("Updating %s in %s",
                         self.secret_format, self)
                self.write(vault_client)
        elif not self.present and not self.existing:
            LOG.info("No %s to remove from %s",
                     self.secret_format, self)
        elif not self.present and self.existing:
            LOG.info("Removing %s from %s",
                     self.secret_format, self)
            self.delete(vault_client)

    def filtered(self):
        """Determines whether or not resource is filtered.
        Resources may be filtered if the tags do not match
        or the user has specified explict paths to include
        or exclude via command line options"""
        if not is_tagged(self.tags, self.opt.tags):
            LOG.info("Skipping %s as it does not have requested tags",
                     self.path)
            return False

        if not specific_path_check(self.path, self.opt):
            LOG.info("Skipping %s as it does not match specified paths",
                     self.path)
            return False

        return True

    @staticmethod
    def diff_write_only(resource):
        """A different implementation of diff that is
        used for those Vault resources that are write-only
        such as AWS root configs"""
        if resource.present and not resource.existing:
            return ADD
        elif not resource.present and resource.existing:
            return DEL
        elif resource.present and resource.existing:
            return OVERWRITE

        return NOOP

    @wrap_vault("reading")
    def read(self, client):
        """Read from Vault while handling non surprising errors."""
        if self.no_resource:
            return

        LOG.debug("Reading from %s", self)
        try:
            return client.read(self.path)
        except hvac.exceptions.InvalidRequest as vault_exception:
            if str(vault_exception).startswith('no handler for route'):
                return None

    @wrap_vault("writing")
    def write(self, client):
        """Write to Vault while handling non-surprising errors."""
        if self.no_resource:
            return

        client.write(self.path, **self.obj())

    @wrap_vault("deleting")
    def delete(self, client):
        """Delete from Vault while handling non-surprising errors."""
        if self.no_resource:
            return

        LOG.debug("Deleting %s", self)
        try:
            client.delete(self.path)
        except (hvac.exceptions.InvalidPath,
                hvac.exceptions.InvalidRequest) \
                as vault_exception:
            if str(vault_exception).startswith('no handler for route'):
                return None


class Secret(Resource):
    """Vault Secrets
    These Vault resources will have some kind of secret backend
    underneath them. Seems to work with generic and AWS"""
    config_key = 'secrets'


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
    secret_format = 'mount point'
    no_resource = True

    def __init__(self, obj, opt):
        super(Mount, self).__init__(obj, opt)
        self.mount = obj['path']
        self.path = self.mount
        self.tunable(obj)


class AuditLog(Resource):
    """Audit Logs
    Only supports syslog and file backends"""
    required_fields = ['type']
    config_key = 'audit_logs'
    no_resource = True

    def __init__(self, log_obj, opt):
        super(AuditLog, self).__init__(log_obj, opt)
        self.backend = log_obj['type']
        self.mount = self.backend
        self.path = log_obj.get('path', self.backend)
        obj = {
            'name': log_obj.get('name', self.backend),
        }
        obj_opt = dict()
        if self.backend == 'file':
            obj_opt['file_path'] = log_obj['file_path']

        if self.backend == 'syslog':
            if 'tag' in log_obj:
                obj_opt['tag'] = log_obj['tag']

            if 'facility' in log_obj:
                obj_opt['facility'] = log_obj['facility']

        if 'description' in log_obj:
            obj_opt['description'] = log_obj['description']

        obj['options'] = obj_opt
        self._obj = obj
        self.tunable(obj)


class Latent(Resource):
    """Latent Secret
    A latent secret is tracked only within icefiles. It will never be
    used as part of interactions with HCVault"""
    required_fields = []
    resource_key = 'latent_file'
    config_key = 'secrets'
    no_resource = True

    def secrets(self):
        return [self.secret]

    def __init__(self, obj, opt):
        super(Latent, self).__init__(obj, opt)
        self.secret = obj['latent_file']

    def obj(self):
        filename = hard_path(self.secret, self.opt.secrets)
        secret_file(filename)
        return open_maybe_binary(filename)
