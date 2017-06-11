"""AWS Secret Backend"""
import yaml
import aomi.exceptions
from aomi.vault import is_mounted
from aomi.model import Secret, Resource
from aomi.helpers import hard_path, merge_dicts, cli_hash, log
from aomi.template import load_var_files, render
from aomi.validation import sanitize_mount, secret_file, check_obj


def grok_ttl(secret):
    """Parses the TTL information"""
    ttl_obj = {}
    lease_msg = ''
    if 'lease' in secret:
        ttl_obj['lease'] = secret['lease']
        lease_msg = "lease:%s" % (ttl_obj['lease'])

    if 'lease_max' in secret:
        ttl_obj['lease_max'] = secret['lease_max']
    elif 'lease' in ttl_obj:
        ttl_obj['lease_max'] = ttl_obj['lease']

    if 'lease_max' in ttl_obj:
        lease_msg = "%s lease_max:%s" % (lease_msg, ttl_obj['lease_max'])

    return ttl_obj, lease_msg


class AWSRole(Resource):
    """AWS Role"""
    required_fields = ['name', ['policy', 'arn']]
    child = True

    def __init__(self, mount, obj, opt):
        super(AWSRole, self).__init__(obj, opt)
        self.path = "%s/roles/%s" % (mount, obj['name'])
        if self.present:
            self._obj = obj
            if 'policy' in self._obj:
                self._obj['policy'] = hard_path(self._obj['policy'],
                                                opt.policies)

    def obj(self):
        s_obj = {}
        if 'policy' in self._obj:
            role_template_obj = self._obj.get('vars', {})
            cli_obj = merge_dicts(load_var_files(self.opt),
                                  cli_hash(self.opt.extra_vars))
            template_obj = merge_dicts(role_template_obj, cli_obj)
            s_obj = {'policy': render(self._obj['policy'], template_obj)}
        elif 'arn' in self._obj:
            s_obj = {'arn': self._obj['arn']}

        return s_obj


class AWSTTL(Resource):
    """AWS Lease"""
    child = True

    def __init__(self, mount, obj, msg, opt):
        super(AWSTTL, self).__init__(obj, opt)
        self.path = "%s/config/lease" % mount
        self._obj = obj
        self.msg = msg


class AWS(Secret):
    """AWS Backend"""
    resource_key = 'aws_file'
    required_fields = [['aws_file', 'aws'], 'mount',
                       'region', 'roles']
    backend = 'aws'

    def resources(self):
        return [
            self,
            self.ttl,
        ] + self.roles

    def fetch(self, vault_client):
        if is_mounted(self.backend,
                      self.mount,
                      vault_client.list_secret_backends()):
            self.existing = True

    def sync(self, vault_client):
        if self.present and not self.existing:
            log("Writing AWS root to %s" % self.path, self.opt)
        elif self.present and self.existing:
            log("Updating AWS root at %s" % self.path, self.opt)

    def obj(self):
        _secret, filename, region = self._obj
        actual_filename = hard_path(filename, self.opt.secrets)
        secret_file(actual_filename)
        aws_obj = yaml.safe_load(open(actual_filename, 'r').read())
        check_obj(['access_key_id', 'secret_access_key'],
                  self, aws_obj)
        return {
            'access_key': aws_obj['access_key_id'],
            'secret_key': aws_obj['secret_access_key'],
            'region': region
        }

    def secrets(self):
        return [self._obj[0]]

    def __init__(self, obj, opt):
        super(AWS, self).__init__(obj, opt)
        self.mount = sanitize_mount(obj['mount'])
        self.path = "%s/config/root" % self.mount
        aws_file_path = obj['aws_file']
        self._obj = (obj['aws_file'],
                     aws_file_path,
                     obj['region'])

        self.roles = []
        for role in obj['roles']:
            self.roles.append(AWSRole(self.mount, role, opt))

        if self.roles is None:
            raise aomi.exceptions.AomiData('missing aws roles')

        ttl_obj, lease_msg = grok_ttl(obj)
        if ttl_obj:
            self.ttl = AWSTTL(self.mount, ttl_obj, lease_msg, opt)
