"""
Authentication Vault Resources
* User/Password auth (with DUO)
* AppRole role creation
* AppID
* Policies
* Syslog/File Audit Log
"""
import logging
import yaml
import hvac
import aomi.exceptions
from aomi.vault import wrap_hvac as wrap_vault
from aomi.helpers import hard_path, merge_dicts, map_val
from aomi.template import load_vars, render
from aomi.model.resource import Auth, Resource, NOOP, ADD
from aomi.validation import secret_file, sanitize_mount
LOG = logging.getLogger(__name__)


class DUOAccess(Resource):
    """DUO API
    Access Credentials"""
    child = True

    def export(self, _directory):
        pass

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

    def diff(self, obj=None):
        return Resource.diff_write_only(self)

    def __init__(self, duo, secret, opt):
        s_obj = {
            'state': 'present'
        }
        if not duo.present:
            s_obj['state'] = 'absent'

        super(DUOAccess, self).__init__(s_obj, opt)
        self.backend = duo.backend
        self.path = "auth/%s/duo/access" % self.backend
        self.filename = secret
        self.secret = secret
        self.host = duo.host

    def fetch(self, vault_client):
        mfa_config = vault_client.read("auth/%s/mfa_config" % self.backend)
        self.existing = mfa_config and mfa_config['data']['type'] == 'duo'


class DUO(Auth):
    """DUO MFA
    Authentication Backend Decorator"""
    required_fields = ['host', 'creds', 'backend']
    resource = 'DUO MFA'
    config_key = 'duo'

    def resources(self):
        return [self, self.access]

    def diff(self, obj=None):
        return Resource.diff_write_only(self)

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


class AppRoleSecret(Resource):
    """Approle Secret"""
    child = True

    def __str__(self):
        return "AppRole Secret %s %s" % (self.role_name, self.secret_name)

    def __init__(self, obj, opt):
        self.role_name = obj['role_name']
        self.secret_name = obj['name']
        self.filename = obj['filename']
        self.opt = opt
        super(AppRoleSecret, self).__init__(obj, opt)

    def diff(self, obj=None):
        if self.existing and 'secret_id_accessor' in self.existing:
            return NOOP

        return ADD

    def obj(self):
        filename = hard_path(self.filename, self.opt.secrets)
        aomi.validation.secret_file(filename)
        handle = open(filename, 'r')
        s_obj = {
            'role_name': self.role_name,
            'secret_name': self.secret_name,
            'secret_id': handle.read().strip()
        }
        handle.close()
        return s_obj

    def secrets(self):
        return [self.filename]

    @wrap_vault("writing")
    def write(self, client):
        s_obj = self.obj()
        secret_id = s_obj['secret_id']
        del s_obj['secret_id']
        client.create_role_custom_secret_id(self.role_name,
                                            secret_id,
                                            s_obj)

    @wrap_vault("reading")
    def read(self, client):
        try:
            return client.get_role_secret_id(self.role_name,
                                             self.obj()['secret_id'])
        except hvac.exceptions.InvalidPath:
            return None
        except ValueError as vault_excep:
            if str(vault_excep).startswith('No JSON object'):
                return None

            raise

    @wrap_vault("deleting")
    def delete(self, client):
        client.delete_role_secret_id(self.role_name,
                                     self.obj()['secret_id'])


class AppRole(Auth):
    """AppRole"""
    required_fields = ['name', 'policies']
    config_key = 'approles'

    def resources(self):
        return [self] + self.secret_ids

    def __init__(self, obj, opt):
        super(AppRole, self).__init__('approle', obj, opt)
        self.app_name = obj['name']
        self.path = "auth/approle/role/%s" % obj['name']
        self.mount = self.backend
        self.secret_ids = []
        policies = obj['policies']
        # HCV seems to always add this in anyway. Having this implicit
        # at our end makes the diff'ing easier.
        if 'default' not in policies:
            policies.insert(0, 'default')

        role_obj = {
            'policies': ','.join(policies)
        }
        map_val(role_obj, obj, 'bound_cidr_list', '', 'cidr_list')
        map_val(role_obj, obj, 'secret_id_num_uses', 0, 'secret_uses')
        map_val(role_obj, obj, 'secret_id_ttl', 0, 'secret_ttl')
        map_val(role_obj, obj, 'period', 0)
        map_val(role_obj, obj, 'token_max_ttl', 0)
        map_val(role_obj, obj, 'token_ttl', 0)
        map_val(role_obj, obj, 'bind_secret_id', True)
        map_val(role_obj, obj, 'token_num_uses', 0)
        self._obj = role_obj
        if 'preset' in obj:
            self.presets(obj['preset'], opt)

    def presets(self, presets, opt):
        """Will create representational objects for any preset (push)
        based AppRole Secrets."""
        for preset in presets:
            secret_obj = dict(preset)
            secret_obj['role_name'] = self.app_name
            self.secret_ids.append(AppRoleSecret(secret_obj, opt))

    def diff(self, obj=None):
        obj = dict(self.obj())
        obj['policies'] = obj['policies'].split(',')
        obj['policies'] = sorted(obj['policies'])
        return super(AppRole, self).diff(obj)

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


class LDAP(Auth):
    """LDAP Authentication"""
    required_fields = ['url']
    config_key = 'ldap_auth'

    def __init__(self, obj, opt):
        super(LDAP, self).__init__('ldap', obj, opt)
        auth_obj = {
            'url': obj['url']
        }
        self.mount = 'ldap'
        self.path = sanitize_mount("auth/ldap/config")
        self.secret = obj.get('secrets')
        map_val(auth_obj, obj, 'starttls', False)
        map_val(auth_obj, obj, 'insecure_tls', False)
        map_val(auth_obj, obj, 'discoverdn')
        map_val(auth_obj, obj, 'userdn')
        map_val(auth_obj, obj, 'userattr')
        map_val(auth_obj, obj, 'deny_null_bind', True)
        map_val(auth_obj, obj, 'upndomain')
        map_val(auth_obj, obj, 'groupfilter')
        map_val(auth_obj, obj, 'groupdn')
        map_val(auth_obj, obj, 'groupattr')
        map_val(auth_obj, obj, 'binddn')
        self._obj = auth_obj

    def obj(self):
        ldap_obj = self._obj
        if self.secret:
            filename = hard_path(self.secret, self.opt.secrets)
            secret_file(filename)

        return ldap_obj


class LDAPGroup(Resource):
    """LDAP Group Policy Mapping"""
    required_fields = ['policies', 'group']
    config_key = 'ldap_groups'

    def __init__(self, obj, opt):
        super(LDAPGroup, self).__init__(obj, opt)
        self.path = sanitize_mount("auth/%s/groups/%s" %
                                   (obj.get('mount', 'ldap'), obj['group']))
        self._obj = {
            "policies": obj['policies']
        }

    def obj(self):
        return {
            'policies': ','.join(self._obj.get('policies', []))
        }


class LDAPUser(Resource):
    """LDAP User Membership"""
    required_fields = ['user']
    config_key = 'ldap_users'

    def __init__(self, obj, opt):
        super(LDAPUser, self).__init__(obj, opt)
        self.path = sanitize_mount("auth/%s/users/%s" %
                                   (obj.get('mount', 'ldap'), obj['user']))
        self._obj = {}
        map_val(self._obj, obj, 'groups', [])
        map_val(self._obj, obj, 'policies', [])

    def obj(self):
        return {
            'groups': ','.join(self._obj.get('groups', [])),
            'policies': ','.join(self._obj.get('policies', []))
        }


class UserPass(Auth):
    """UserPass"""
    required_fields = ['username', 'password_file', 'policies']
    config_key = 'users'

    def export(self, _directory):
        pass

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

    def diff(self, obj=None):
        return Resource.diff_write_only(self)

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
            self.filename = obj['file']
            base_obj = load_vars(opt)
            self._obj = merge_dicts(base_obj, obj.get('vars', {}))

    def validate(self, obj):
        super(Policy, self).validate(obj)
        if 'vars' in obj and not isinstance(obj['vars'], dict):
            raise aomi.exceptions.Validation('policy vars must be dicts')

    def obj(self):
        return render(hard_path(self.filename, self.opt.policies), self._obj) \
            .lstrip() \
            .strip() \
            .replace("\n\n", "\n")

    @wrap_vault("reading")
    def read(self, client):
        LOG.debug("Reading %s", self)
        a_policy = client.get_policy(self.path)
        if a_policy:
            return a_policy.lstrip() \
                           .strip() \
                           .replace("\n\n", "\n")

        return None

    @wrap_vault("writing")
    def write(self, client):
        client.set_policy(self.path, self.obj())

    @wrap_vault("deleting")
    def delete(self, client):
        LOG.debug("Deleting %s", self)
        client.delete_policy(self.path)
