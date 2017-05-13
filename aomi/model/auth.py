import yaml
import hvac
import aomi.exceptions
import aomi.legacy
from aomi.vault import app_id_name
from aomi.helpers import hard_path, merge_dicts, cli_hash, log
from aomi.template import load_var_files, render
from aomi.model import Auth, Resource, wrap_vault
from aomi.validation import secret_file, sanitize_mount


class DUOAccess(Resource):
    required_fields = ['key', 'secret']
    child = True
    resource = 'DUO API'

    def __init__(self, duo, obj):
        super(DUOAccess, self).__init__(obj)
        self.backend = duo.backend
        self.path = "auth/%s/duo/access" % self.backend
        self.duo_path = duo.path
        self.obj = {
            'host': duo.host,
            'skey': obj['secret'],
            'ikey': obj['key']
        }

    def fetch(self, vault_client, opt):
        self.existing = False  # always assume because we can never be sure


class DUO(Auth):
    required_fields = ['host', 'creds', 'backend']
    resource = 'DUO MFA'
    config_key = 'duo'

    def resources(self):
        return [self, self.access]

    def __init__(self, obj, opt):
        super(DUO, self).__init__('userpass', obj)
        self.path = "auth/%s/mfa_config" % self.backend
        self.host = obj['host']
        self.mount = 'userpass'
        self.obj = {
            'type': 'duo'
        }
        creds_file_name = hard_path(obj['creds'], opt.secrets)
        aomi.validation.secret_file(creds_file_name)
        creds = yaml.safe_load(open(creds_file_name).read())
        self.access = DUOAccess(self, creds)


class AppUser(Resource):
    required_fields = ['id']
    resource = 'App User'
    child = True

    def __init__(self, app, obj, opt):
        super(AppUser, self).__init__(obj, opt)
        self.path = "auth/app-id/map/user-id/%s" % obj['id']
        self.obj = {
            'value': app.name
        }
        if 'cidr' in obj:
            self.obj['cidr'] = obj['cidr']


class App(Auth):
    required_fields = ['app_file', 'policy_name']
    resource = 'App ID'
    config_key = 'apps'

    def __init__(self, obj, opt):
        super(App, self).__init__('app-id', obj)
        self.name = app_id_name(obj)
        self.mount = 'app-id'
        app_file = hard_path(obj['app_file'], opt.secrets)
        aomi.validation.secret_file(app_file)
        secret_obj = yaml.safe_load(open(app_file).read())
        self.id = aomi.legacy.app_id_itself(obj, secret_obj)
        self.path = "auth/app-id/map/app-id/%s" % self.id

        if 'users' not in secret_obj:
            raise aomi.exceptions.AomiData("Invalid app file %s" % app_file)

        if 'policy' in obj:
            raise aomi \
                .exceptions \
                .AomiData("Inline AppID Policies are no longer supported")

        self.obj = {
            'value': obj['policy_name'],
            'display_name': self.name
        }
        self.users = []
        for user in self.obj.get('users', []):
            self.users.append(AppUser(self, user, opt))

    def resources(self):
        return [self] + self.users


class AppRole(Auth):
    required_fields = ['name', 'policies']
    resource = 'App Role'
    config_key = 'approles'

    def __init__(self, obj, opt):
        super(AppRole, self).__init__('approle', obj)
        self.name = obj['name']
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

        self.obj = role_obj

    @wrap_vault("writing")
    def write(self, client, opt):
        client.create_role(self.name, **self.obj)

    @wrap_vault("reading")
    def read(self, client, opt):
        try:
            return client.get_role(self.name)
        except hvac.exceptions.InvalidPath:
            return None

    @wrap_vault("deleting")
    def delete(self, client, opt):
        client.delete_role(self.name)


class UserPass(Auth):
    required_fields = ['username', 'password_file', 'policies']
    resource = 'UserPass Spec'
    config_key = 'users'

    def __init__(self, obj, opt):
        super(UserPass, self).__init__('userpass', obj)
        self.name = obj['username']
        self.mount = 'userpass'
        self.path = sanitize_mount("auth/userpass/users/%s" % self.name)
        self.validate(obj)
        self.policies = obj['policies']
        password_file = hard_path(obj['password_file'],
                                  opt.secrets)
        secret_file(password_file)
        self.password = open(password_file).readline().strip()
        self.obj = {
            'password': self.password,
            'policies': ','.join(self.policies)
        }


class Policy(Resource):
    resource = "Vault Policy"
    required_fields = ['file', 'name']
    config_key = 'policies'

    def __init__(self, obj, opt):
        super(Policy, self).__init__(obj)
        self.path = obj['name']
        if self.present:
            self.filename = hard_path(obj['file'], opt.policies)
            cli_obj = merge_dicts(load_var_files(opt),
                                  cli_hash(opt.extra_vars))
            self.obj = merge_dicts(cli_obj, obj.get('vars', {}))

    def validate(self, obj):
        super(Policy, self).validate(obj)
        if 'vars' in obj and not isinstance(obj['vars'], dict):
            raise aomi.exceptions.Validation('policy vars must be dicts')

    def policy_data(self):
        return render(self.filename, self.obj)

    @wrap_vault("reading")
    def read(self, client, opt):
        log("Reading %s" % (self), opt)
        return client.get_policy(self.path)

    @wrap_vault("writing")
    def write(self, client, opt):
        client.set_policy(self.path, self.policy_data())

    @wrap_vault("deleting")
    def delete(self, client, opt):
        log("Deleting %s" % (self), opt)
        client.delete_policy(self.path)
