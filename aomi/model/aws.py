import yaml
import aomi.legacy
from aomi.vault import is_mounted
from aomi.model import Secret, Resource
from aomi.helpers import hard_path, warning, merge_dicts, cli_hash, log
from aomi.template import load_var_files, render
from aomi.validation import sanitize_mount, secret_file, check_obj


def grok_ttl(secret, aws_obj):
    """Parses the TTL information, keeping in mind old format"""
    ttl_obj = {}
    lease_msg = ''
    if 'lease' in secret:
        ttl_obj['lease'] = secret['lease']
        lease_msg = "lease:%s" % (ttl_obj['lease'])

    if 'lease_max' in secret:
        ttl_obj['lease_max'] = secret['lease_max']
    else:
        if 'lease' in ttl_obj:
            ttl_obj['lease_max'] = ttl_obj['lease']

    if lease_msg == '':
        if 'lease' in aws_obj:
            ttl_obj['lease'] = aws_obj['lease']
            lease_msg = "lease:%s" % (ttl_obj['lease'])

        if 'lease_max' in aws_obj:
            ttl_obj['lease_max'] = aws_obj['lease_max']
        else:
            if 'lease' in ttl_obj:
                ttl_obj['lease_max'] = ttl_obj['lease']

        if lease_msg != '':
            # see https://github.com/Autodesk/aomi/issues/40
            warning('Setting lease and lease_max from the '
                    'AWS yaml is deprecated')

    if 'lease_max' in ttl_obj:
        lease_msg = "%s lease_max:%s" % (lease_msg, ttl_obj['lease_max'])

    return ttl_obj, lease_msg


class AWSRole(Resource):
    required_fields = ['name', ['policy', 'arn']]
    resource = 'AWS Role'
    child = True

    def __init__(self, mount, obj, opt):
        super(AWSRole, self).__init__(obj)
        self.path = "%s/roles/%s" % (mount, obj['name'])
        if self.present:
            if 'policy' in obj:
                self.filename = hard_path(obj['policy'], opt.policies)
                role_template_obj = obj.get('vars', {})
                cli_obj = merge_dicts(load_var_files(opt),
                                      cli_hash(opt.extra_vars))
                template_obj = merge_dicts(role_template_obj, cli_obj)
                self.obj = {
                    'policy': render(self.filename, template_obj)
                }
            elif 'arn' in obj:
                self.obj = {'arn': obj['arn']}


class AWSTTL(Resource):
    resource = 'AWS Lease'
    child = True

    def __init__(self, mount, obj, msg, _opt):
        super(AWSTTL, self).__init__(obj)
        self.path = "%s/config/lease" % mount
        self.obj = obj
        self.msg = msg


class AWS(Secret):
    resource = 'AWS Backend'
    resource_key = 'aws_file'
    required_fields = [['aws_file', 'aws'], 'mount']
    backend = 'aws'

    def resources(self):
        return [
            self,
            self.ttl,
        ] + self.roles

    def fetch(self, vault_client, opt):
        if is_mounted(self.backend,
                      self.mount,
                      vault_client.list_secret_backends()):
            self.existing = True

    def sync(self, vault_client, opt):
        if self.present and not self.existing:
            log("Writing AWS root to %s" % self.path, opt)
        elif self.present and self.existing:
            log("Updating AWS root at %s" % self.path, opt)

    def __init__(self, obj, opt):
        super(AWS, self).__init__(obj)
        self.mount = sanitize_mount(obj['mount'])
        self.path = "%s/config/root" % self.mount
        aws_file_path = hard_path(obj['aws_file'], opt.secrets)
        secret_file(aws_file_path)
        aws_obj = yaml.safe_load(open(aws_file_path, 'r').read())
        check_obj(['access_key_id', 'secret_access_key'],
                  "aws secret %s" % (aws_file_path),
                  aws_obj)

        self.region = aomi.legacy.aws_region(obj, aws_obj)
        if self.region is None:
            raise aomi.exceptions.AomiData('missing aws region')

        self.roles = []
        for role in aomi.legacy.aws_roles(obj, aws_obj):
            self.roles.append(AWSRole(self.mount, role, opt))

        if self.roles is None:
            raise aomi.exceptions.AomiData('missing aws roles')

        self.obj = {
            'access_key': aws_obj['access_key_id'],
            'secret_key': aws_obj['secret_access_key'],
            'region': self.region
        }
        ttl_obj, lease_msg = grok_ttl(obj, aws_obj)
        if ttl_obj:
            self.ttl = AWSTTL(self.mount, ttl_obj, lease_msg, opt)
