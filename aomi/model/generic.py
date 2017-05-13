from copy import deepcopy
from uuid import uuid4
import yaml
import aomi.exceptions
from aomi.model import Secret
from aomi.helpers import hard_path, log, random_word
from aomi.validation import sanitize_mount, secret_file, check_obj


class Generic(Secret):
    backend = 'generic'

    def __init__(self, obj, _opt):
        super(Generic, self).__init__(obj)
        self.mount = sanitize_mount(obj['mount'])
        self.path = "%s/%s" % (self.mount, obj['path'])


class VarFile(Generic):
    required_fields = ['path', 'mount', 'var_file']
    resource = 'Generic VarFile'
    resource_key = 'var_file'

    def __init__(self, obj, opt):
        super(VarFile, self).__init__(obj, opt)
        self.filename = hard_path(obj['var_file'], opt.secrets)
        secret_file(self.filename)
        self.obj = yaml.safe_load(open(self.filename).read())


class Files(Generic):
    resource = 'Generic File'
    required_fields = ['path', 'mount', 'files']
    resource_key = 'files'

    def __init__(self, obj, opt):
        super(Files, self).__init__(obj, opt)
        s_obj = {}
        for sfile in obj['files']:
            filename = hard_path(sfile['source'], opt.secrets)
            secret_file(filename)
            data = open(filename, 'r').read()
            s_obj[sfile['name']] = data

        self.obj = s_obj

    def validate(self, obj):
        super(Files, self).validate(obj)
        for fileobj in obj['files']:
            check_obj(['source', 'name'], self.resource, fileobj)


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
    resource = 'Generic Generated'
    required_fields = ['mount', 'path', 'keys']
    resource_key = 'generated'
    # TODO: why are generated generics stored slight differently

    def __init__(self, obj, opt):
        super(Generated, self).__init__(obj['generated'], opt)
        for key in obj['generated']['keys']:
            check_obj(['name', 'method'], 'generated secret entry', key)
        self.keys = obj['generated']['keys']

    def generate_obj(self, opt):
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
                log("Not overwriting %s/%s" % (self.path, key_name), opt)
                continue
            else:
                secret_obj[key_name] = generated_key(key, opt)

        return secret_obj

    def sync(self, vault_client, opt):
        gen_obj = self.generate_obj(opt)
        self.obj = gen_obj
        super(Generated, self).sync(vault_client, opt)
