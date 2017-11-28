""" Secret rendering """
from __future__ import print_function
import os
import sys
import logging
from future.utils import iteritems  # pylint: disable=E0401
from pkg_resources import resource_filename
import hvac
from cryptorito import portable_b64decode, is_base64
from aomi.helpers import merge_dicts, cli_hash, \
    path_pieces, abspath
from aomi.template import render, load_vars
from aomi.vault import renew_secret, is_aws
import aomi.exceptions
LOG = logging.getLogger(__name__)


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
        return abspath(src)

    builtin = src.split(':')[1]
    builtin = "templates/%s.j2" % builtin
    return resource_filename(__name__, builtin)


def blend_vars(secrets, opt):
    """Blends secret and static variables together"""
    base_obj = load_vars(opt)
    merged = merge_dicts(base_obj, secrets)
    template_obj = dict((k, v) for k, v in iteritems(merged) if v)
    # give templates something to iterate over
    template_obj['aomi_items'] = template_obj.copy()
    return template_obj


def template(client, src, dest, paths, opt):
    """Writes a template using variables from a vault path"""
    key_map = cli_hash(opt.key_map)
    obj = {}
    for path in paths:
        response = client.read(path)
        if not response:
            raise aomi.exceptions.VaultData("Unable to retrieve %s" % path)
        if is_aws(response['data']) and 'sts' not in path:
            renew_secret(client, response, opt)

        for s_k, s_v in response['data'].items():
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
    write_raw_file(output, abspath(dest))


def write_raw_file(secret, dest):
    """Writes an actual secret out to a file"""
    secret_file = None
    secret_filename = abspath(dest)
    if sys.version_info >= (3, 0):
        if not isinstance(secret, str):
            secret_file = open(secret_filename, 'wb')

    if not secret_file:
        secret_file = open(secret_filename, 'w')

    secret_file.write(secret)
    secret_file.close()
    os.chmod(secret_filename, 0o600)


def raw_file(client, src, dest, opt):
    """Write the contents of a vault path/key to a file. Is
    smart enough to attempt and handle binary files that are
    base64 encoded."""
    path, key = path_pieces(src)
    resp = client.read(path)
    if not resp:
        client.revoke_self_token()
        raise aomi.exceptions.VaultData("Unable to retrieve %s" % path)
    else:
        if 'data' in resp and key in resp['data']:
            secret = resp['data'][key]
            if is_base64(secret):
                LOG.debug('decoding base64 entry')
                secret = portable_b64decode(secret)

            if is_aws(resp['data']) and 'sts' not in path:
                renew_secret(client, resp, opt)

            write_raw_file(secret, dest)
        else:
            client.revoke_self_token()
            e_msg = "Key %s not found in %s" % (key, path)
            raise aomi.exceptions.VaultData(e_msg)


def env(client, paths, opt):
    """Renders a shell snippet based on paths in a Secretfile"""
    old_prefix = False
    old_prefix = opt.prefix and not (opt.add_prefix or
                                     opt.add_suffix or
                                     not opt.merge_path)
    if old_prefix:
        LOG.warning("the prefix option is deprecated "
                    "please use"
                    "--no-merge-path --add-prefix $OLDPREFIX_ instead")
    elif opt.prefix:
        LOG.warning("the prefix option is deprecated"
                    "please use"
                    "--no-merge-path --add-prefix $OLDPREFIX_ instead")
    key_map = cli_hash(opt.key_map)
    for path in paths:
        secrets = client.read(path)
        if secrets and 'data' in secrets:
            if is_aws(secrets['data']) and 'sts' not in path:
                renew_secret(client, secrets, opt)

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


def aws(client, path, opt):
    """Renders a shell environment snippet with AWS information"""

    try:
        creds = client.read(path)
    except (hvac.exceptions.InternalServerError) as vault_exception:
        # this is how old vault behaves
        if vault_exception.errors[0].find('unsupported path') > 0:
            emsg = "Invalid AWS path. Did you forget the" \
                   " credential type and role?"
            raise aomi.exceptions.AomiFile(emsg)
        else:
            raise

    # this is how new vault behaves
    if not creds:
        emsg = "Invalid AWS path. Did you forget the" \
               " credential type and role?"
        raise aomi.exceptions.AomiFile(emsg)

    renew_secret(client, creds, opt)

    if creds and 'data' in creds:
        print("AWS_ACCESS_KEY_ID=\"%s\"" % creds['data']['access_key'])
        print("AWS_SECRET_ACCESS_KEY=\"%s\"" % creds['data']['secret_key'])
        if 'security_token' in creds['data'] \
           and creds['data']['security_token']:
            token = creds['data']['security_token']
            print("AWS_SECURITY_TOKEN=\"%s\"" % token)
    else:
        client.revoke_self_token()
        e_msg = "Unable to generate AWS credentials from %s" % path
        raise aomi.exceptions.VaultData(e_msg)

    if opt.export:
        print("export AWS_ACCESS_KEY_ID")
        print("export AWS_SECRET_ACCESS_KEY")
        if 'security_token' in creds['data'] \
           and creds['data']['security_token']:
            print("export AWS_SECURITY_TOKEN")
