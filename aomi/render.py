""" Secret rendering """
import os
from jinja2 import Template
from aomi.helpers import problems


def template(client, src, dest, vault_path):
    """Writes a template using variables from a vault path"""
    template_src = Template(open(os.path.abspath(src), 'r').read())
    secrets = client.read(vault_path)
    if not secrets:
        problems("Unable to retrieve %s" % vault_path)

    obj = {}
    for k, v in secrets['data'].items():
        norm_path = [x for x in vault_path.split('/') if x]
        v_name = ("%s_%s" % ('_'.join(norm_path), k)).lower()
        obj[v_name] = v

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


def env(client, path, opt):
    """Renders a shell snippet based on paths in a Secretfile"""
    secrets = client.read(path)
    if secrets and 'data' in secrets:
        for s_key, s_val in secrets['data'].items():
            if opt.prefix:
                env_name = "%s_%s" % (opt.prefix.upper(), s_key.upper())
            else:
                env_bits = path.split('/')
                env_bits.append(s_key)
                env_name = '_'.join(env_bits).upper()

            print("%s=\"%s\"" % (env_name, s_val))
            if opt.export:
                print("export %s" % env_name)


def aws(client, path, opt):
    """Renders a shell environment snippet with AWS information"""
    creds = client.read(path)
    if creds and 'data' in creds:
        print("AWS_ACCESS_KEY_ID=\"%s\"" % creds['data']['access_key'])
        print("AWS_SECRET_ACCESS_KEY=\"%s\"" % creds['data']['secret_key'])
        if 'security_token' in creds['data']:
            token = creds['data']['security_token']
            print("AWS_SECURITY_TOKEN=\"%s\"" % token)
    else:
        problems("Unable to generate AWS credentials from %s" % path)

    if opt.export:
        print("export AWS_ACCESS_KEY_ID")
        print("export AWS_SECRET_ACCESS_KEY")
        if 'security_token' in creds['data']:
            print("export AWS_SECURITY_TOKEN")
