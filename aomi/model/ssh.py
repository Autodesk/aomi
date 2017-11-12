""" SSH Dynamic Credentials """
from aomi.model.resource import Secret
from aomi.validation import sanitize_mount


class SSHRole(Secret):
    """SSH Credential Backend"""
    resource_key = 'ssh_creds'
    required_fields = ['key_type']
    backend = 'ssh'

    def __init__(self, obj, opt):
        super(SSHRole, self).__init__(obj, opt)
        self.mount = sanitize_mount(obj.get('mount', 'ssh'))
        a_name = obj.get('name', obj['ssh_creds'])
        self.path = "%s/roles/%s" % (self.mount, a_name)
        self._obj = {
            'key_type': obj['key_type']
        }
        if 'cidr_list' in obj:
            self._obj['cidr_list'] = obj['cidr_list']

        if 'default_user' in obj:
            self._obj['default_user'] = obj['default_user']

        self.tunable(obj)
