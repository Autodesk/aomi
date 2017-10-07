""" SSH Dynamic Credentials """
from aomi.model.resource import Secret
from aomi.validation import sanitize_mount


class SSHRole(Secret):
    """SSH Credential Backend"""
    resource_key = 'ssh_creds'
    required_fields = ['name', 'key_type']
    backend = 'ssh_role'

    def __init__(self, obj, opt):
        super(SSHRole, self).__init__(obj, opt)
        self.mount = sanitize_mount(obj['mount'])
        self.path = "%s/roles/%s" % (self.mount, obj['name'])
        self._obj = {
            'key_type': obj['key_type']
        }
        if 'cidr_list' in obj:
            self._obj['cidr_list'] = obj['cidr_list']

        if 'default_user' in obj:
            self._obj['default_user'] = obj['default_user']
