"""Handles the various kinds of secret seeding which we do"""
import os
import re
from uuid import uuid4
import yaml
import hvac
from aomi.helpers import problems, hard_path, log, \
    warning, merge_dicts, cli_hash, random_word
import aomi.validation
from aomi.validation import sanitize_mount
from aomi.template import render, load_var_files


def is_mounted(mount, backends, style):
    """Determine whether a backend of a certain type is mounted"""
    for mount_name, values in backends.items():
        b_norm = '/'.join([x for x in mount_name.split('/') if x])
        m_norm = '/'.join([x for x in mount.split('/') if x])
        if (m_norm == b_norm) and values['type'] == style:
            return True

    return False


def ensure_mounted(client, backend, mount):
    """Will ensure a mountpoint exists, or bail with a polite error"""
    backends = client.list_secret_backends()
    if not is_mounted(mount, backends, backend):
        try:
            client.enable_secret_backend(backend, mount_point=mount)
        except hvac.exceptions.InvalidRequest as exception:
            match = re.match('existing mount at (?P<path>.+)', str(exception))
            if match:
                problems("%s has a mountpoint conflict with %s" %
                         (mount, match.group('path')))
            else:
                raise exception


def ensure_auth(client, auth):
    """Will ensure a particular auth endpoint is mounted"""
    backends = client.list_auth_backends().keys()
    backends = [x.rstrip('/') for x in backends]
    if auth not in backends:
        client.enable_auth_backend(auth)


def validate_entry(obj, path, opt):
    """Determins whether or not to interpret this particular
    aomi construct based on combination of tags and what
    is passed via the CLI"""
    if not aomi.validation.tag_check(obj, path, opt):
        return False

    if not aomi.validation.specific_path_check(path, opt):
        return False

    return True


def var_file(client, secret, opt):
    """Seed a var_file into Vault"""
    aomi.validation.var_file_obj(secret)
    my_mount = sanitize_mount(secret['mount'])
    path = "%s/%s" % (my_mount, secret['path'])
    var_file_name = hard_path(secret['var_file'], opt.secrets)
    aomi.validation.secret_file(var_file_name)
    varz = yaml.load(open(var_file_name).read())

    if not validate_entry(secret, path, opt):
        return

    ensure_mounted(client, 'generic', my_mount)

    if opt.mount_only:
        log("Only mounting %s" % my_mount, opt)
        return

    client.write(path, **varz)
    log('wrote var_file %s into %s/%s' % (
        var_file_name,
        my_mount,
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
    aomi.validation.aws_file_obj(secret)

    my_mount = sanitize_mount(secret['mount'])
    aws_path = "%s/config/root" % my_mount
    if not validate_entry(secret, aws_path, opt):
        return

    ensure_mounted(client, 'aws', my_mount)

    if opt.mount_only:
        log("Only mounting %s" % my_mount, opt)
        return

    aws_file_path = hard_path(secret['aws_file'], opt.secrets)
    aomi.validation.secret_file(aws_file_path)

    aws_obj = yaml.load(open(aws_file_path, 'r').read())
    aomi.validation.aws_secret_obj(aws_file_path, aws_obj)

    region = aws_region(secret, aws_obj)

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
    """Handles the seeding of roles associated with an AWS account"""
    for role in roles:
        aomi.validation.aws_role_obj(role)

        role_path = "%s/roles/%s" % (mount, role['name'])
        if role.get('state', 'present') == 'present':
            if 'policy' in role:
                role_file = hard_path(role['policy'], opt.policies)
                role_template_obj = role.get('vars', {})
                cli_obj = merge_dicts(load_var_files(opt),
                                      cli_hash(opt.extra_vars))
                obj = merge_dicts(role_template_obj, cli_obj)
                data = render(role_file, obj)
                log('writing inline role %s from %s' %
                    (role['name'], role_file), opt)
                client.write(role_path, policy=data)
            elif 'arn' in role:
                log('writing role %s for %s' %
                    (role['name'], role['arn']), opt)
                client.write(role_path, arn=role['arn'])
        else:
            log('removing role %s' % role['name'], opt)
            client.delete(role_path)


def app_users(client, app_id, p_users):
    """Write out users for an application"""
    for user in p_users:
        if 'id' not in user:
            problems("Invalid user definition %s" % user)

        user_path = "auth/app-id/map/user-id/%s" % user['id']
        user_obj = {'value': app_id}
        if 'cidr' in user:
            user_obj['cidr_block'] = user['cidr']

        client.write(user_path, **user_obj)


def app_id_name(app_obj):
    """Determines the proper app id name"""
    name = None
    if 'name' in app_obj:
        name = app_obj['name']
    else:
        name = os.path.splitext(os.path.basename(app_obj['app_file']))[0]

    return name


def app_id_policy_file(app_obj, data):
    """Determines the correct policy file name, checking both the
    proper and legacy location"""
    policy_file = None
    if 'policy' in data:
        warning('Defining policy_name within the app yaml is deprecated')
        policy_file = data['policy']
    elif 'policy' in app_obj:
        policy_file = app_obj['policy']

    return policy_file


def app_id_policy_name(app_obj, data):
    """Determines the policy name, checking both the proper
    and the legacy location"""
    policy_name = None
    if 'policy_name' in data:
        warning('Defining policy_name within the app yaml is deprecated')
        policy_name = data['policy_name']
    elif 'policy_name' in data:
        policy_name = app_obj['policy_name']
    else:
        policy_name = app_id_name(app_obj)

    return policy_name


def app_id_itself(app_obj, data):
    """Determines the application ID to use"""
    app_id = None
    if 'app_id' in data:
        warning('Defining app_id within the app yaml is deprecated')
        app_id = data['app_id']
    elif 'app_id' in app_obj:
        app_id = app_obj['app_id']
    else:
        app_id = app_id_name(app_obj)

    return app_id


def app(client, app_obj, opt):
    """Seed an app file into Vault"""
    if 'app_file' not in app_obj:
        problems("Invalid app definition %s" % app_obj)

    name = app_id_name(app_obj)
    if not validate_entry(app_obj, "app-id/%s" % name, opt):
        return

    app_file = hard_path(app_obj['app_file'], opt.secrets)
    aomi.validation.secret_file(app_file)
    data = yaml.load(open(app_file).read())

    ensure_auth(client, 'app-id')
    if opt.mount_only:
        log("Only enabling app-id", opt)
        return

    if 'users' not in data:
        problems("Invalid app file %s" % app_file)

    policy_name = app_id_policy_name(app_obj, data)
    app_id = app_id_itself(app_obj, data)
    policy_file = app_id_policy_file(app_obj, data)

    if policy_file:
        p_data = policy_data(policy_file, app_obj.get('policy_vars', {}), opt)
        if policy_name in client.list_policies():
            if p_data != client.get_policy(policy_name):
                problems("Policy %s already exists and content differs"
                         % policy_name)

        write_policy(policy_name, p_data, client, opt)
    else:
        if policy_name not in client.list_policies():
            problems("Policy %s is not inline but does not exist"
                     % policy_name)

        log("Using existing policy %s" % policy_name, opt)

    app_path = "auth/app-id/map/app-id/%s" % app_id
    app_obj = {'value': policy_name, 'display_name': name}
    client.write(app_path, **app_obj)
    r_users = data.get('users', [])
    app_users(client, app_id, r_users)
    log('created %d users in application %s' % (len(r_users), name), opt)


def files(client, secret, opt):
    """Seed files into Vault"""
    aomi.validation.file_obj(secret)
    obj = {}
    my_mount = sanitize_mount(secret['mount'])
    vault_path = "%s/%s" % (my_mount, secret['path'])
    if not validate_entry(secret, vault_path, opt):
        return

    ensure_mounted(client, 'generic', my_mount)
    if opt.mount_only:
        log("Only mounting %s" % my_mount, opt)
        return

    for sfile in secret.get('files', []):
        if 'source' not in sfile or 'name' not in sfile:
            problems("Invalid file specification %s" % sfile)

        filename = hard_path(sfile['source'], opt.secrets)
        aomi.validation.secret_file(filename)
        data = open(filename, 'r').read()
        obj[sfile['name']] = data
        log('writing file %s into %s/%s' % (
            filename,
            vault_path,
            sfile['name']), opt)

    client.write(vault_path, **obj)


def policy_data(file_name, policy_vars, opt):
    """Returns the rendered policy"""
    policy_path = hard_path(file_name, opt.policies)
    cli_obj = merge_dicts(load_var_files(opt),
                          cli_hash(opt.extra_vars))
    obj = merge_dicts(policy_vars, cli_obj)
    return render(policy_path, obj)


def write_policy(policy_name, data, client, opt):
    """Actually write a policy to vault (renders as a template first)"""
    log('writing policy %s' % policy_name, opt)
    client.set_policy(policy_name, data)


def policy(client, secret, opt):
    """Seed a standalone policy into Vault"""
    aomi.validation.policy_obj(secret)

    policy_name = secret['name']
    if not validate_entry(secret, "policy/%s" % policy_name, opt):
        return

    if secret.get('state', 'present') == 'present':
        data = policy_data(secret['file'], secret.get('vars', {}), opt)
        write_policy(policy_name, data, client, opt)
    else:
        log('removing policy %s' % policy_name, opt)
        client.delete_policy(policy_name)


def audit_logs(client, log_obj, opt):
    """Creates an audit log entry in Vault"""
    aomi.validation.audit_log_obj(log_obj)
    log_type = log_obj['type']
    vault_path = log_obj.get('path', log_type)
    if not aomi.validation.tag_check(log_obj, vault_path, opt):
        return

    existing_backends = client.list_audit_backends()['data']
    audit_path = "%s/" % vault_path
    if audit_path in existing_backends.keys():
        if log_type == existing_backends[audit_path]['type']:
            log("audit log %s already exists" % vault_path, opt)
            return
        else:
            problems("conflicting audit log at %s" % vault_path)

    obj = {
        'type': log_obj['type']
    }
    if log_type == 'file':
        obj['file_path'] = log_obj['file_path']

    if log_type == 'syslog':
        if 'tag' in log_obj:
            obj['tag'] = log_obj['tag']

        if 'facility' in log_obj:
            obj['facility'] = log_obj['facility']

    if 'description' in log_obj:
        client.enable_audit_backend(log_type,
                                    description=log_obj['description'],
                                    options=obj,
                                    name=vault_path)
    else:
        client.enable_audit_backend(log_type,
                                    options=obj,
                                    name=vault_path)

    log("created %s audit log at %s" % (log_type, vault_path), opt)


def users(client, user_obj, opt):
    """Creates userpass users in Vault"""
    aomi.validation.user_obj(user_obj)

    name = user_obj['username']

    if not aomi.validation.tag_check(user_obj,
                                     "userpass/%s" % name,
                                     opt):
        return

    password_file = hard_path(user_obj['password_file'],
                              opt.secrets)
    aomi.validation.secret_file(password_file)
    password = open(password_file).readline().strip()

    ensure_auth(client, 'userpass')

    user_path = "auth/userpass/users/%s" % name
    v_obj = {
        'password': password,
        'policies': ','.join(user_obj['policies'])
    }
    client.write(user_path, **v_obj)


def approle(client, approle_obj, opt):
    """Will seed application role information into a Vault"""
    aomi.validation.approle_obj(approle_obj)
    name = approle_obj['name']
    if not aomi.validation.tag_check(approle_obj,
                                     "approle/%s" % name,
                                     opt):
        return

    ensure_auth(client, 'approle')

    policies = approle_obj['policies']

    role_obj = {
        'policies': ','.join(policies)
    }

    if 'cidr_list' in approle_obj:
        role_obj['bound_cidr_list'] = ','.join(approle_obj['cidr_list'])
    else:
        role_obj['bound_cidr_list'] = ''

    if 'secret_uses' in approle_obj:
        role_obj['secret_id_num_uses'] = approle_obj['secret_uses']

    if 'secret_ttl' in approle_obj:
        role_obj['secret_id_ttl'] = approle_obj['secret_ttl']

    log("creating approle %s" % name, opt)
    client.create_role(name, **role_obj)


def generated(client, obj, opt):
    """Will provision some random strings into vault, as requested"""
    aomi.validation.generated_obj(obj)
    my_mount = sanitize_mount(obj['mount'])
    vault_path = "%s/%s" % (my_mount, obj['path'])
    if not aomi.validation.tag_check(obj, vault_path, opt):
        return
    ensure_mounted(client, 'generic', my_mount)
    if opt.mount_only:
        log("Only mounting %s" % my_mount, opt)
        return

    existing = {}
    resp = client.read(vault_path)
    if resp:
        existing = resp['data']

    secret_obj = {}
    for key in obj['keys']:
        key_name = key['name']
        if key_name in existing and not key.get('overwrite'):
            log("Not overwriting %s/%s" % (vault_path, key_name), opt)
            continue

        if key['method'] == 'uuid':
            log("Setting %s to a uuid" % key_name, opt)
            secret_obj[key_name] = str(uuid4())
        elif key['method'] == 'words':
            log("Setting %s to random words" % key_name, opt)
            secret_obj[key_name] = random_word()
        else:
            problems("Unexpected generated secret method %s" % key['method'])

    genseclen = len(secret_obj.keys())
    if genseclen > 0:
        update_msg = "Writing %s generated secrets to %s" % \
                     (genseclen, vault_path)
        log(update_msg, opt)
        client.write(vault_path, **secret_obj)
