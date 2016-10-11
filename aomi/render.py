""" Secret rendering """
import os
from pkg_resources import resource_filename
from aomi.helpers import problems, warning, cli_hash, merge_dicts
from aomi.template import render, load_var_files


def secret_key_name(path, key, opt):
    """Renders a Secret key name appropriately"""
    value = key
    if opt.merge_path:
        norm_path = [x for x in path.split('/') if x]
        value = "%s_%s" % ('_'.join(norm_path), key)

    if opt.add_prefix:
        value = "%s%s" % (opt.add_prefix, value)

    if opt.add_suffix:
        value = "%s%s" % (value, opt.add_suffix)

    return value


def grok_template_file(src):
    """Determine the real deal template file"""
    if not src.startswith('builtin:'):
        return os.path.abspath(src)
    else:
        builtin = src.split(':')[1]
        builtin = "templates/%s.j2" % builtin
        return resource_filename(__name__, builtin)


def blend_vars(secrets, opt):
    """Blends secret and static variables together"""
    extra_obj = merge_dicts(load_var_files(opt),
                            cli_hash(opt.extra_vars))
    template_obj = merge_dicts(extra_obj, secrets)
    # give templates something to iterate over
    template_obj['aomi_items'] = template_obj.copy()
    return template_obj


def template(client, src, dest, paths, opt):
    """Writes a template using variables from a vault path"""
    key_map = cli_hash(opt.key_map)
    obj = {}
    for path in paths:
        data = client.read(path)['data']
        for s_k, s_v in data.items():
            o_key = s_k
            if s_k in key_map:
                o_key = key_map[s_k]

            k_name = secret_key_name(path, o_key, opt) \
                .lower() \
                .replace('-', '_')
            obj[k_name] = s_v

    template_obj = blend_vars(obj, opt)
    output = render(grok_template_file(src),
                    template_obj)
    open(os.path.abspath(dest), 'w').write(output)


def raw_file(client, src, dest):
    """Write the contents of a vault path/key to a file"""
    path_bits = src.split('/')
    path = '/'.join(path_bits[0:len(path_bits) - 1])
    key = path_bits[len(path_bits) - 1]
    resp = client.read(path)
    if not resp:
        problems("Unable to retrieve %s" % path, client)
    else:
        if 'data' in resp and key in resp['data']:
            secret = resp['data'][key]
            open(os.path.abspath(dest), 'w').write(secret)
        else:
            problems("Key %s not found in %s" % (key, path), client)


def env(client, paths, opt):
    """Renders a shell snippet based on paths in a Secretfile"""
    old_prefix = False
    old_prefix = opt.prefix and not (opt.add_prefix or
                                     opt.add_suffix or
                                     not opt.merge_path)
    if old_prefix:
        warning("the prefix option is deprecated but being used "
                "due to not passing in new options")
    elif opt.prefix:
        warning("the prefix option is deprecated but not being "
                "used due to passing in new options")
    key_map = cli_hash(opt.key_map)
    for path in paths:
        secrets = client.read(path)
        if secrets and 'data' in secrets:
            for s_key, s_val in secrets['data'].items():
                o_key = s_key
                if s_key in key_map:
                    o_key = key_map[s_key]

                # see https://github.com/Autodesk/aomi/issues/40
                env_name = None
                if old_prefix:
                    env_name = ("%s_%s" % (opt.prefix, o_key)).upper()
                else:
                    env_name = secret_key_name(path, o_key, opt).upper()

                print("%s=\"%s\"" % (env_name, s_val))
                if opt.export:
                    print("export %s" % env_name)


def grok_seconds(lease):
    """Ensures that we are returning just seconds"""
    if lease.endswith('s'):
        return int(lease[0:-1])
    elif lease.endswith('m'):
        return int(lease[0:-1] * 60)
    elif lease.endswith('h'):
        return int(lease[0:-1] * 3600)
    else:
        return None


def aws(client, path, opt):
    """Renders a shell environment snippet with AWS information"""
    creds = client.read(path)
    seconds = grok_seconds(opt.lease)
    if not seconds:
        problems("Passed in invalid lease type %s" % opt.lease, client)

    renew = client.renew_secret(creds['lease_id'], seconds)
    # sometimes it takes a bit for vault to respond
    # if we are within 5s then we are fine
    if seconds - renew['lease_duration'] >= 5:
        problems('Unable to renew secret with desired lease', client)

    if creds and 'data' in creds:
        print("AWS_ACCESS_KEY_ID=\"%s\"" % creds['data']['access_key'])
        print("AWS_SECRET_ACCESS_KEY=\"%s\"" % creds['data']['secret_key'])
        if 'security_token' in creds['data'] \
           and creds['data']['security_token']:
            token = creds['data']['security_token']
            print("AWS_SECURITY_TOKEN=\"%s\"" % token)
    else:
        problems("Unable to generate AWS credentials from %s" % path, client)

    if opt.export:
        print("export AWS_ACCESS_KEY_ID")
        print("export AWS_SECRET_ACCESS_KEY")
        if 'security_token' in creds['data'] \
           and creds['data']['security_token']:
            print("export AWS_SECURITY_TOKEN")
