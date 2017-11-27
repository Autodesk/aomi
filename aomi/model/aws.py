"""AWS Secret Backend"""
import logging
import aomi.exceptions
import aomi.model.resource
from aomi.vault import is_mounted
from aomi.model.resource import Secret, Resource
from aomi.helpers import hard_path, merge_dicts
from aomi.template import load_vars, render, load_var_file
from aomi.validation import sanitize_mount, secret_file, check_obj
LOG = logging.getLogger(__name__)


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
        if 'policy' in obj:
            self.filename = obj['policy']

        if self.present:
            self._obj = obj
            if 'policy' in self._obj:
                self._obj['policy'] = hard_path(self.filename, opt.policies)

    def export(self, directory):
        if not hasattr(self, 'filename'):
            return

        secret_h = self.export_handle(directory)
        secret_h.write(self.obj()['policy'])
        secret_h.close()

    def obj(self):
        s_obj = {}
        if 'policy' in self._obj:
            role_template_obj = self._obj.get('vars', {})
            base_obj = load_vars(self.opt)
            template_obj = merge_dicts(role_template_obj, base_obj)
            aws_role = render(self._obj['policy'], template_obj)
            aws_role = aws_role.replace(" ", "").replace("\n", "")
            s_obj = {'policy': aws_role}
        elif 'arn' in self._obj:
            s_obj = {'arn': self._obj['arn']}

        return s_obj


class AWSTTL(Resource):
    """AWS Lease"""
    child = True

    def __init__(self, mount, obj, opt):
        super(AWSTTL, self).__init__(obj, opt)
        self.path = "%s/config/lease" % mount
        self._obj = obj


class AWS(Secret):
    """AWS Backend"""
    resource_key = 'aws_file'
    required_fields = [['aws_file', 'aws'], 'mount',
                       'region', 'roles']
    backend = 'aws'

    def resources(self):
        pieces = [self]
        if self.present:
            pieces = pieces + [self.ttl] + self.roles

        return pieces

    def diff(self, obj=None):
        return Resource.diff_write_only(self)

    def fetch(self, vault_client):
        if is_mounted(self.backend,
                      self.mount,
                      vault_client.list_secret_backends()):
            self.existing = True

    def sync(self, vault_client):
        if self.present:
            LOG.info("Writing AWS root to %s", self.path)
            self.write(vault_client)
        else:
            LOG.info("Removing AWS root at %s", self.path)
            self.delete(vault_client)

    def obj(self):
        _secret, filename, region = self._obj
        actual_filename = hard_path(filename, self.opt.secrets)
        secret_file(actual_filename)
        template_obj = load_vars(self.opt)
        aws_obj = load_var_file(actual_filename, template_obj)
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
        if self.present:
            self._obj = (obj['aws_file'],
                         aws_file_path,
                         obj['region'])

            self.roles = []
            for role in obj['roles']:
                self.roles.append(AWSRole(self.mount, role, opt))

            if self.roles is None:
                raise aomi.exceptions.AomiData('missing aws roles')

            ttl_obj, _lease_msg = grok_ttl(obj)
            if ttl_obj:
                self.ttl = AWSTTL(self.mount, ttl_obj, opt)

        self.tunable(obj)
