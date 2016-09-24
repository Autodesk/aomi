""" Secret rendering """
import os
from jinja2 import Template
from aomi.helpers import problems, warning

def secret_key_name(path, key, opt):
    """Renders a Secret key name appropriately"""
    value = key
    if opt.merge_path:
        norm_path = [x for x in path.split('/') if x]
        value = "%s_%s" % ('_'.join(norm_path), key)

    if opt.prefix:
        value = "%s%s" % (opt.prefix, value)

    if opt.suffix:
        value = "%s%s" % (value, opt.suffix)

    return value


def template(client, src, dest, paths, opt):
    """Writes a template using variables from a vault path"""
    template_src = Template(open(os.path.abspath(src), 'r').read())
    obj = {}
    for path in paths:
        data = client.read(path)['data']
        for s_k, s_v in data.items():
            k_name = secret_key_name(path, s_k, opt) \
                    .lower() \
                    .replace('-', '_')
            obj[k_name] = s_v

    output = template_src.render(**obj)
    open(os.path.abspath(dest), 'w').write(output)


def raw_file(client, src, dest):
    """Write the contents of a vault path/key to a file"""
    path_bits = src.split('/')
    path = '/'.join(path_bits[0:len(path_bits) - 1])
    key = path_bits[len(path_bits) - 1]
    resp = client.read(path)
    if not resp:
        problems("Unable to retrieve %s" % path)
    else:
        if 'data' in resp and key in resp['data']:
            secret = resp['data'][key]
            open(os.path.abspath(dest), 'w').write(secret)
        else:
            problems("Key %s not found in %s" % (key, path))


def env(client, paths, opt):
    """Renders a shell snippet based on paths in a Secretfile"""
    for path in paths:
        secrets = client.read(path)
        if secrets and 'data' in secrets:
            for s_key, s_val in secrets['data'].items():
                if opt.prefix:
                    warning("the prefix option is deprecated")
                    env_name = ("%s_%s" % (opt.prefix, s_key)).upper
                env_name = secret_key_name(path, s_key, opt) \
                        .upper()

                print("%s=\"%s\"" % (env_name, s_val))
                if opt.export:
                    print("export %s" % env_name)


def aws(client, path, opt):
    """Renders a shell environment snippet with AWS information"""
    creds = client.read(path)
    if creds and 'data' in creds:
        print("AWS_ACCESS_KEY_ID=\"%s\"" % creds['data']['access_key'])
        print("AWS_SECRET_ACCESS_KEY=\"%s\"" % creds['data']['secret_key'])
        if 'security_token' in creds['data'] \
           and creds['data']['security_token']:
            token = creds['data']['security_token']
            print("AWS_SECURITY_TOKEN=\"%s\"" % token)
    else:
        problems("Unable to generate AWS credentials from %s" % path)

    if opt.export:
        print("export AWS_ACCESS_KEY_ID")
        print("export AWS_SECRET_ACCESS_KEY")
        if 'security_token' in creds['data'] \
           and creds['data']['security_token']:
            print("export AWS_SECURITY_TOKEN")
