"""
Authentication Vault Resources
* User/Password auth (with DUO)
* AppRole role creation
* AppID
* Policies
* Syslog/File Audit Log
"""
import yaml
import hvac
import aomi.exceptions
from aomi.helpers import hard_path, merge_dicts, cli_hash, log
from aomi.template import load_var_files, render
from aomi.model import Auth, Resource, wrap_vault
from aomi.validation import secret_file, sanitize_mount


class DUOAccess(Resource):
    """DUO API
    Access Credentials"""
    child = True

    def secrets(self):
        return [self.secret]

    def obj(self):
        filename = hard_path(self.filename, self.opt.secrets)
        aomi.validation.secret_file(filename)
        obj = yaml.safe_load(open(filename).read())
        return {
            'host': self.host,
            'skey': obj['secret'],
            'ikey': obj['key']
        }

    def __init__(self, duo, secret, opt):
        super(DUOAccess, self).__init__({}, opt)
        self.path = "auth/%s/duo/access" % duo.backend
        self.filename = secret
        self.secret = secret
        self.host = duo.host

    def fetch(self, _vault_client):
        self.existing = False  # always assume because we can never be sure


class DUO(Auth):
    """DUO MFA
    Authentication Backend Decorator"""
    required_fields = ['host', 'creds', 'backend']
    resource = 'DUO MFA'
    config_key = 'duo'

    def resources(self):
        return [self, self.access]

    def __init__(self, obj, opt):
        super(DUO, self).__init__('userpass', obj, opt)
        self.path = "auth/%s/mfa_config" % self.backend
        self.host = obj['host']
        self.mount = 'userpass'
        self._obj = {'type': 'duo'}
        self.access = DUOAccess(self, obj['creds'], opt)


class AppUser(Resource):
    """App User"""
    required_fields = ['id']
    child = True

    def __init__(self, app, obj, opt):
        super(AppUser, self).__init__(obj, opt)
        self.path = "auth/app-id/map/user-id/%s" % obj['id']
        self._obj = {
            'value': app.app_name
        }
        if 'cidr' in obj:
            self._obj['cidr'] = obj['cidr']


class AppRole(Auth):
    """AppRole"""
    required_fields = ['name', 'policies']
    config_key = 'approles'

    def __init__(self, obj, opt):
        super(AppRole, self).__init__('approle', obj, opt)
        self.app_name = obj['name']
        self.path = '%s'
        self.mount = self.backend
        role_obj = {
            'policies': ','.join(obj['policies'])
        }
        if 'cidr_list' in obj:
            role_obj['bound_cidr_list'] = ','.join(obj['cidr_list'])
        else:
            role_obj['bound_cidr_list'] = ''

        if 'secret_uses' in obj:
            role_obj['secret_id_num_uses'] = obj['secret_uses']

        if 'secret_ttl' in obj:
            role_obj['secret_id_ttl'] = obj['secret_ttl']

        self._obj = role_obj

    @wrap_vault("writing")
    def write(self, client):
        client.create_role(self.app_name, **self.obj())

    @wrap_vault("reading")
    def read(self, client):
        try:
            return client.get_role(self.app_name)
        except hvac.exceptions.InvalidPath:
            return None

    @wrap_vault("deleting")
    def delete(self, client):
        client.delete_role(self.app_name)


class UserPass(Auth):
    """UserPass"""
    required_fields = ['username', 'password_file', 'policies']
    config_key = 'users'

    def __init__(self, obj, opt):
        super(UserPass, self).__init__('userpass', obj, opt)
        self.username = obj['username']
        self.mount = 'userpass'
        self.path = sanitize_mount("auth/userpass/users/%s" % self.username)
        self.policies = obj['policies']
        self.secret = obj['password_file']
        self.filename = self.secret

    def secrets(self):
        return [self.secret]

    def obj(self):
        filename = hard_path(self.filename, self.opt.secrets)
        secret_file(filename)
        password = open(filename).readline().strip()
        return {
            'password': password,
            'policies': ','.join(self.policies)
        }


class Policy(Resource):
    """Vault Policy"""
    required_fields = ['file', 'name']
    config_key = 'policies'

    def __init__(self, obj, opt):
        super(Policy, self).__init__(obj, opt)
        self.path = obj['name']
        if self.present:
            self.filename = hard_path(obj['file'], opt.policies)
            cli_obj = merge_dicts(load_var_files(opt),
                                  cli_hash(opt.extra_vars))
            self._obj = merge_dicts(cli_obj, obj.get('vars', {}))

    def validate(self, obj):
        super(Policy, self).validate(obj)
        if 'vars' in obj and not isinstance(obj['vars'], dict):
            raise aomi.exceptions.Validation('policy vars must be dicts')

    @wrap_vault("reading")
    def read(self, client):
        log("Reading %s" % (self), self.opt)
        return client.get_policy(self.path)

    @wrap_vault("writing")
    def write(self, client):
        client.set_policy(self.path, render(self.filename, self._obj))

    @wrap_vault("deleting")
    def delete(self, client):
        log("Deleting %s" % (self), self.opt)
        client.delete_policy(self.path)
