"""
Generic Vault Resources
* YAML Variable Files
* Static files
* Generated/Random Secrets
"""
import os
from copy import deepcopy
from uuid import uuid4
import logging
import hvac.exceptions
from future.utils import iteritems  # pylint: disable=E0401
from cryptorito import portable_b64encode
from aomi.vault import wrap_hvac as wrap_vault
import aomi.exceptions
from aomi.model.resource import Secret
from aomi.helpers import random_word, hard_path, \
    open_maybe_binary
from aomi.template import load_vars, load_var_file
from aomi.validation import sanitize_mount, secret_file, check_obj, \
    is_unicode_string
LOG = logging.getLogger(__name__)


class Generic(Secret):
    """Generic Secrets"""
    backend = 'kv'

    def __init__(self, obj, opt):
        super(Generic, self).__init__(obj, opt)
        self.mount = sanitize_mount(obj['mount'])
        self.path = obj['path']
        self.kv_version = None

    def __str__(self):
        return "%s %s/%s" % (self.name(), self.mount, self.path)

    # There has to be a better way to wrap the cubbyhole token dance?
    def vault_kv(self, client, functions, *args, **kwargs):
        """Wrap KV1/2 commands in a way that allows the tooling to
        magically juggle tokens for the cubbyhole. This is required
        because while aomi makes use of a short lived operational
        token, anything written to the cubbyhole must be associated
        with the initial token"""

        cubbyhole = False
        kv_api = client.secrets.kv.v2
        if self.mount == 'cubbyhole':
            cubbyhole = True
            client.token = client.initial_token

        if self.kv_version == 1:
            kv_api = client.secrets.kv.v1
            kv_fun = functions[0]
        else:
            if len(functions) == 1:
                kv_fun = functions[0]
            else:
                kv_fun = functions[1]

        # do something?
        resp = None
        try:
            resp = getattr(kv_api, kv_fun)(self.path, *args, **kwargs)
        finally:
            if cubbyhole:
                client.token = client.operational_token

        return resp

    @wrap_vault("writing")
    def write(self, client):
        self.vault_kv(client,
                      ['create_or_update_secret'],
                      self.obj(),
                      mount_point=self.mount)

    @wrap_vault("reading")
    def read(self, client):
        try:
            return self.vault_kv(client,
                                 ['read_secret', 'read_secret_version'],
                                 mount_point=self.mount)
        except hvac.exceptions.InvalidPath:
            return None

    @wrap_vault("reading")
    def delete(self, client):
        self.vault_kv(client,
                      ['delete_secret', 'delete_latest_version_of_secret'],
                      mount_point=self.mount)


class VarFile(Generic):
    """Generic VarFile"""
    required_fields = ['path', 'mount', 'var_file']
    resource_key = 'var_file'

    def secrets(self):
        return [self.secret]

    def __init__(self, obj, opt):
        super(VarFile, self).__init__(obj, opt)
        self.secret = obj['var_file']
        self.filename = obj['var_file']

    def obj(self):
        filename = hard_path(self.filename, self.opt.secrets)
        secret_file(filename)
        template_obj = load_vars(self.opt)
        return load_var_file(filename, template_obj)


class Files(Generic):
    """Generic File"""
    required_fields = ['path', 'mount', 'files']
    resource_key = 'files'

    def secrets(self):
        return [v for _k, v in iteritems(self._obj)]

    def __init__(self, obj, opt):
        super(Files, self).__init__(obj, opt)
        s_obj = {}
        for sfile in obj['files']:
            s_obj[sfile['name']] = sfile['source']

        self._obj = s_obj

    def export(self, directory):
        for name, filename in iteritems(self._obj):
            dest_file = "%s/%s" % (directory, filename)
            dest_dir = os.path.dirname(dest_file)
            if not os.path.isdir(dest_dir):
                os.mkdir(dest_dir, 0o700)

            secret_h = open(dest_file, 'w')
            secret_h.write(self.existing[name])
            secret_h.close()

    def obj(self):
        s_obj = {}
        for name, filename in iteritems(self._obj):
            actual_file = hard_path(filename, self.opt.secrets)
            secret_file(actual_file)
            data = open_maybe_binary(actual_file)
            try:
                is_unicode_string(data)
                s_obj[name] = data
            except aomi.exceptions.Validation:
                s_obj[name] = portable_b64encode(data)
                self.resource_format = 'binary'

        return s_obj

    def validate(self, obj):
        super(Files, self).validate(obj)
        for fileobj in obj['files']:
            check_obj(['source', 'name'], self.name(), fileobj)


def generated_key(key):
    """Create the proper generated key value"""
    key_name = key['name']
    if key['method'] == 'uuid':
        LOG.debug("Setting %s to a uuid", key_name)
        return str(uuid4())
    elif key['method'] == 'words':
        LOG.debug("Setting %s to random words", key_name)
        return random_word()
    elif key['method'] == 'static':
        if 'value' not in key.keys():
            raise aomi.exceptions.AomiData("Missing static value")

        LOG.debug("Setting %s to a static value", key_name)
        return key['value']
    else:
        raise aomi.exceptions.AomiData("Unexpected generated secret method %s"
                                       % key['method'])


class Generated(Generic):
    """Generic Generated"""
    required_fields = ['mount', 'path', 'keys']
    resource_key = 'generated'
    # why are generated generics stored slight differently

    def __init__(self, obj, opt):
        super(Generated, self).__init__(obj['generated'], opt)
        for key in obj['generated']['keys']:
            check_obj(['name', 'method'], 'generated secret entry', key)
        self.keys = obj['generated']['keys']

    def generate_obj(self):
        """Generates the secret object, respecting existing information
        and user specified options"""
        secret_obj = {}
        if self.existing:
            secret_obj = deepcopy(self.existing)

        for key in self.keys:
            key_name = key['name']
            if self.existing and \
               key_name in self.existing and \
               not key.get('overwrite'):
                LOG.debug("Not overwriting %s/%s", self.path, key_name)
                continue
            else:
                secret_obj[key_name] = generated_key(key)

        return secret_obj

    def diff(self, obj=None):
        if self.present and not self.existing:
            return aomi.model.resource.ADD
        elif not self.present and self.existing:
            return aomi.model.resource.DEL
        elif self.present and self.existing:
            overwrites = [x for x in self.keys if x.get('overwrite')]
            if overwrites:
                return aomi.model.resource.OVERWRITE

        return aomi.model.resource.NOOP

    def sync(self, vault_client):
        gen_obj = self.generate_obj()
        self._obj = gen_obj
        super(Generated, self).sync(vault_client)
