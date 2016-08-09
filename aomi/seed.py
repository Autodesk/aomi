import os
import re
import yaml
import hvac
from aomi.helpers import problems, hard_path, log, is_tagged


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

    client.write(path, **varz)
    log('wrote var_file %s into %s/%s' % (
        var_file_name,
        secret['mount'],
        secret['path']), opt)


def aws(client, secret, opt):
    """Seed an aws_file into Vault"""
    if 'aws_file' not in secret or 'mount' not in secret:
        problems("Invalid aws secret definition" % secret)

    aws_file_path = hard_path(secret['aws_file'], opt.secrets)
    aws_obj = yaml.load(open(aws_file_path, 'r').read())

    if 'access_key_id' not in aws_obj \
       or 'secret_access_key' not in aws_obj \
       or 'region' not in aws_obj \
       or 'roles' not in aws_obj:
        problems("Invalid AWS secrets" % aws)

    aws_path = "%s/config/root" % secret['mount']
    if not is_tagged(secret.get('tags', []), opt.tags):
        log("Skipping %s as it does not have appropriate tags" %
            aws_path, opt)
        return

    ensure_mounted(client, 'aws', secret['mount'])

    obj = {
        'access_key': aws_obj['access_key_id'],
        'secret_key': aws_obj['secret_access_key'],
        'region': aws_obj['region']
    }
    client.write(aws_path, **obj)
    log('wrote aws_file %s into %s' % (
        aws_file_path,
        aws_path), opt)

    ttl_obj = {}
    lease_msg = ''
    if 'lease' in aws_obj:
        ttl_obj['lease'] = aws_obj['lease']
        lease_msg = "%s lease:%s" % (lease_msg, ttl_obj['lease'])

    if 'lease_max' in aws_obj:
        ttl_obj['lease_max'] = aws_obj['lease_max']
    else:
        if 'lease' in ttl_obj:
            ttl_obj['lease_max'] = ttl_obj['lease']

    if 'lease_max' in ttl_obj:
        lease_msg = "%s lease_max:%s" % (lease_msg, ttl_obj['lease_max'])

    if ttl_obj:
        client.write("%s/config/lease" % (secret['mount']), **ttl_obj)
        log("Updated lease for %s %s" % (secret['mount'], lease_msg), opt)

    for role in aws_obj['roles']:
        if 'policy' not in role or 'name' not in role:
            problems("Invalid role definition %s" % role)

        data = open(hard_path(role['policy'], opt.policies), 'r').read()
        role_path = "%s/roles/%s" % (secret['mount'], role['name'])
        client.write(role_path, policy=data)


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

    app_file = hard_path(app_obj['app_file'], opt.secrets)
    data = yaml.load(open(app_file).read())
    if 'app_id' not in data \
       or 'policy' not in data:
        problems("Invalid app file %s" % app_file)

    policy_name = None
    if 'policy_name' in data:
        policy_name = data['policy_name']
    else:
        policy_name = name

    policy = open(hard_path(data['policy'], opt.policies), 'r').read()
    client.set_policy(name, policy)
    app_path = "auth/app-id/map/app-id/%s" % data['app_id']
    app_obj = {'value': policy_name, 'display_name': name}
    client.write(app_path, **app_obj)
    users = data.get('users', [])
    for user in users:
        if 'id' not in user:
            problems("Invalid user definition %s" % user)

        user_path = "auth/app-id/map/user-id/%s" % user['id']
        user_obj = {'value': data['app_id']}
        if 'cidr' in user:
            user_obj['cidr_block'] = user['cidr']

        client.write(user_path, **user_obj)

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

    ensure_mounted(client, 'generic', secret['mount'])

    client.write(vault_path, **obj)
