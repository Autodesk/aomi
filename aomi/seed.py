import os
import re
import yaml
import hvac
from aomi.helpers import problems, hard_path, log, is_tagged, warning


def is_mounted(mount, backends, style):
    """Determine whether a backend of a certain type is mounted"""
    for m, v in backends.items():
        b_norm = '/'.join([x for x in m.split('/') if x])
        m_norm = '/'.join([x for x in mount.split('/') if x])
        if (m_norm == b_norm) and v['type'] == style:
            return True

    return False


def ensure_mounted(client, backend, mount):
    """Will ensure a mountpoint exists, or bail with a polite error"""
    backends = client.list_secret_backends()
    if not is_mounted(mount, backends, backend):
        try:
            client.enable_secret_backend(backend, mount_point=mount)
        except hvac.exceptions.InvalidRequest as e:
            m = re.match('existing mount at (?P<path>.+)', str(e))
            if m:
                problems("%s has a mountpoint conflict with %s" %
                         (mount, m.group('path')))


def ensure_auth(client, auth):
    """Will ensure a particular auth endpoint is mounted"""
    backends = client.list_auth_backends()['data'].keys()
    backends = [x.rstrip('/') for x in backends]
    if auth not in backends:
        client.enable_auth_backend(auth)


def var_file(client, secret, opt):
    """Seed a var_file into Vault"""
    path = "%s/%s" % (secret['mount'], secret['path'])
    var_file_name = hard_path(secret['var_file'], opt.secrets)
    varz = yaml.load(open(var_file_name).read())
    if 'var_file' not in secret \
       or 'mount' not in secret \
       or 'path' not in secret:
        problems("Invalid generic secret definition %s" % secret)

    if not is_tagged(secret.get('tags', []), opt.tags):
        log("Skipping %s as it does not have appropriate tags" % path, opt)
        return

    ensure_mounted(client, 'generic', secret['mount'])

    if opt.mount_only:
        log("Only mounting %s" % secret['mount'], opt)
        return

    client.write(path, **varz)
    log('wrote var_file %s into %s/%s' % (
        var_file_name,
        secret['mount'],
        secret['path']), opt)


def aws_region(secret, aws_obj):
    """Return the AWS region with appropriate output"""
    if 'region' in secret:
        return secret['region']
    elif 'region' in aws_obj:
        # see https://github.com/Autodesk/aomi/issues/40
        warning('Defining region in the AWS yaml is deprecated')
        return aws_obj['region']
    else:
        problems('AWS region is not defined')


def aws_roles(secret, aws_obj):
    """Return the AWS roles with appropriate output"""
    if 'roles' in secret:
        return secret['roles']
    elif 'roles' in aws_obj:
        # see https://github.com/Autodesk/aomi/issues/40
        warning('Defining roles within the AWS yaml is deprecated')
        return aws_obj['roles']
    else:
        problems('No AWS roles defined')


def aws(client, secret, opt):
    """Seed an aws_file into Vault"""
    if ('aws_file' not in secret and 'aws' not in secret) \
       or 'mount' not in secret:
        problems("Invalid aws secret definition" % secret)

    aws_file_path = hard_path(secret['aws_file'], opt.secrets)
    aws_obj = yaml.load(open(aws_file_path, 'r').read())

    if 'access_key_id' not in aws_obj \
       or 'secret_access_key' not in aws_obj:
        problems("Invalid AWS secrets" % aws)

    region = aws_region(secret, aws_obj)

    aws_path = "%s/config/root" % secret['mount']
    if not is_tagged(secret.get('tags', []), opt.tags):
        log("Skipping %s as it does not have appropriate tags" %
            aws_path, opt)
        return

    ensure_mounted(client, 'aws', secret['mount'])

    if opt.mount_only:
        log("Only mounting %s" % secret['mount'], opt)
        return

    obj = {
        'access_key': aws_obj['access_key_id'],
        'secret_key': aws_obj['secret_access_key'],
        'region': region
    }
    client.write(aws_path, **obj)
    log('wrote aws secrets %s into %s' % (
        aws_file_path,
        aws_path), opt)

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

    if ttl_obj:
        client.write("%s/config/lease" % (secret['mount']), **ttl_obj)
        log("Updated lease for %s %s" % (secret['mount'], lease_msg), opt)

    roles = aws_roles(secret, aws_obj)

    seed_aws_roles(client, secret['mount'], roles, opt)


def seed_aws_roles(client, mount, roles, opt):
    for role in roles:
        if 'name' not in role or \
           ('policy' not in role and 'arn' not in role):
            problems("Invalid role definition %s" % role)

        role_path = "%s/roles/%s" % (mount, role['name'])
        if 'policy' in role:
            data = open(hard_path(role['policy'], opt.policies), 'r').read()
            client.write(role_path, policy=data)
        elif 'arn' in role:
            client.write(role_path, arn=role['arn'])


def app_users(client, app_id, users):
    """Write out users for an application"""
    for user in users:
        if 'id' not in user:
            problems("Invalid user definition %s" % user)

        user_path = "auth/app-id/map/user-id/%s" % user['id']
        user_obj = {'value': app_id}
        if 'cidr' in user:
            user_obj['cidr_block'] = user['cidr']

        client.write(user_path, **user_obj)


def app(client, app_obj, opt):
    """Seed an app file into Vault"""
    if 'app_file' not in app_obj:
        problems("Invalid app definition %s" % app_obj)

    name = None
    if 'name' in app_obj:
        name = app_obj['name']
    else:
        name = os.path.splitext(os.path.basename(app_obj['app_file']))[0]

    if not is_tagged(app_obj.get('tags', []), opt.tags):
        log("Skipping %s as it does not have appropriate tags" % name, opt)
        return

    ensure_auth(client, 'app-id')
    if opt.mount_only:
        log("Only enabling app-id", opt)
        return

    app_file = hard_path(app_obj['app_file'], opt.secrets)
    data = yaml.load(open(app_file).read())
    if 'app_id' not in data \
       or ('policy' not in data and 'policy_name' not in data):
        problems("Invalid app file %s" % app_file)

    policy_name = None
    if 'policy_name' in data:
        policy_name = data['policy_name']
    else:
        policy_name = name

    if 'policy' in data:
        policy_data = open(hard_path(data['policy'], opt.policies), 'r').read()
        if policy_name in client.list_policies():
            if policy_data != client.get_policy(policy_name):
                problems("Policy %s already exists and content differs"
                         % policy_name)

        log("Using inline policy %s" % policy_name, opt)
        client.set_policy(name, policy_data)
    else:
        if policy_name not in client.list_policies():
            problems("Policy %s is not inline but does not exist"
                     % policy_name)

        log("Using existing policy %s" % policy_name, opt)

    app_path = "auth/app-id/map/app-id/%s" % data['app_id']
    app_obj = {'value': policy_name, 'display_name': name}
    client.write(app_path, **app_obj)
    users = data.get('users', [])
    app_users(client, data['app_id'], users)
    log('created %d users in application %s' % (len(users), name), opt)


def files(client, secret, opt):
    """Seed files into Vault"""
    if 'mount' not in secret or 'path' not in secret:
        problems("Invalid files specification %s" % secret)

    obj = {}
    vault_path = "%s/%s" % (secret['mount'], secret['path'])
    if not is_tagged(secret.get('tags', []), opt.tags):
        log("Skipping %s as it does not have appropriate tags" %
            vault_path, opt)
        return

    ensure_mounted(client, 'generic', secret['mount'])
    if opt.mount_only:
        log("Only mounting %s" % secret['mount'], opt)
        return

    for f in secret.get('files', []):
        if 'source' not in f or 'name' not in f:
            problems("Invalid file specification %s" % f)

        filename = hard_path(f['source'], opt.secrets)
        data = open(filename, 'r').read()
        obj[f['name']] = data
        log('writing file %s into %s/%s' % (
            filename,
            vault_path,
            f['name']), opt)

    client.write(vault_path, **obj)


def policy(client, secret, opt):
    """Seed a standalone policy into Vault"""
    if 'name' not in secret or 'file' not in secret:
        problems("Invalid policy specification %s" % secret)

    policy_name = secret['name']
    if not is_tagged(secret.get('tags', []), opt.tags):
        log("Skipping policy %s as it does not have appropriate tags" %
            policy_name, opt)
        return

    policy_data = open(hard_path(secret['file'], opt.policies), 'r').read()
    log('writing policy %s' % policy_name, opt)
    client.set_policy(policy_name, policy_data)
