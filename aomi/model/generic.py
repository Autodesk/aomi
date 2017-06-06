"""
Generic Vault Resources
* YAML Variable Files
* Static files
* Generated/Random Secrets
"""
from copy import deepcopy
from uuid import uuid4
import yaml
from future.utils import iteritems  # pylint: disable=E0401
import aomi.exceptions
from aomi.model import Secret
from aomi.helpers import log, random_word, hard_path, \
    open_maybe_binary, portable_b64encode
from aomi.validation import sanitize_mount, secret_file, check_obj, \
    is_unicode_string


class Generic(Secret):
    """Generic Secrets"""
    backend = 'generic'

    def __init__(self, obj, opt):
        super(Generic, self).__init__(obj, opt)
        self.mount = sanitize_mount(obj['mount'])
        self.path = "%s/%s" % (self.mount, obj['path'])


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
        return yaml.safe_load(open(filename).read())


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
                self.secret_format = 'binary'

        return s_obj

    def validate(self, obj):
        super(Files, self).validate(obj)
        for fileobj in obj['files']:
            check_obj(['source', 'name'], self.name(), fileobj)


def generated_key(key, opt):
    """Create the proper generated key value"""
    key_name = key['name']
    if key['method'] == 'uuid':
        log("Setting %s to a uuid" % key_name, opt)
        return str(uuid4())
    elif key['method'] == 'words':
        log("Setting %s to random words" % key_name, opt)
        return random_word()
    elif key['method'] == 'static':
        if 'value' not in key.keys():
            raise aomi.exceptions.AomiData("Missing static value")

        log("Setting %s to a static value" % key_name, opt)
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
                log("Not overwriting %s/%s" % (self.path, key_name), self.opt)
                continue
            else:
                secret_obj[key_name] = generated_key(key, self.opt)

        return secret_obj

    def sync(self, vault_client):
        gen_obj = self.generate_obj()
        self._obj = gen_obj
        super(Generated, self).sync(vault_client)
