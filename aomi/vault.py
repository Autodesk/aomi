""" Vault interactions """
from __future__ import print_function
import os
import socket
import hvac
import yaml
# need to override those SSL warnings
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from aomi.helpers import log, cli_hash, merge_dicts, abspath
import aomi.seed
from aomi.template import render, load_var_files
from aomi.error import output as error_output
import aomi.error
import aomi.exceptions

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def approle_token(vault_client, role_id, secret_id):
    """Returns a vault token based on the role and seret id"""
    resp = vault_client.auth_approle(role_id, secret_id)
    if 'auth' in resp and 'client_token' in resp['auth']:
        return resp['auth']['client_token']
    else:
        raise aomi.exceptions.AomiCredentials('invalid approle')


def app_token(vault_client, app_id, user_id):
    """Returns a vault token based on the app and user id."""
    resp = vault_client.auth_app_id(app_id, user_id)
    if 'auth' in resp and 'client_token' in resp['auth']:
        return resp['auth']['client_token']
    else:
        raise aomi.exceptions.AomiCredentials('invalid apptoken')


def initial_token(vault_client, opt):
    """Generate our first token based on workstation configuration"""
    home = os.environ['HOME'] if 'HOME' in os.environ else \
        os.environ['USERPROFILE']

    token_file = os.environ.get('VAULT_TOKEN_FILE',
                                os.path.join(home, ".vault-token"))
    app_file = os.environ.get('AOMI_APP_FILE',
                              os.path.join(home, ".aomi-app-token"))
    token_file = abspath(token_file)
    app_file = abspath(app_file)
    if 'VAULT_TOKEN' in os.environ and len(os.environ['VAULT_TOKEN']) > 0:
        log('Token derived from VAULT_TOKEN environment variable', opt)
        return os.environ['VAULT_TOKEN'].strip()
    elif 'VAULT_USER_ID' in os.environ and \
         'VAULT_APP_ID' in os.environ and \
         len(os.environ['VAULT_USER_ID']) > 0 and \
         len(os.environ['VAULT_APP_ID']) > 0:
        token = app_token(vault_client,
                          os.environ['VAULT_APP_ID'].strip(),
                          os.environ['VAULT_USER_ID'].strip())
        log("Token derived from VAULT_APP_ID and VAULT_USER_ID", opt)
        return token
    elif 'VAULT_ROLE_ID' in os.environ and \
         'VAULT_SECRET_ID' in os.environ and \
         len(os.environ['VAULT_ROLE_ID']) > 0 and \
         len(os.environ['VAULT_SECRET_ID']) > 0:
        token = approle_token(vault_client,
                              os.environ['VAULT_ROLE_ID'],
                              os.environ['VAULT_SECRET_ID'])
        log("Token derived from VAULT_ROLE_ID and VAULT_SECRET_ID", opt)
        return token
    elif os.path.exists(app_file):
        token = yaml.load(open(app_file).read().strip())
        if 'app_id' in token and 'user_id' in token:
            token = app_token(vault_client,
                              token['app_id'],
                              token['user_id'])
            log("Token derived from %s" % app_file, opt)
            return token
    elif os.path.exists(token_file):
        log("Token derived from %s" % token_file, opt)
        return open(token_file, 'r').read().strip()
    else:
        raise aomi.exceptions.AomiCredentials('unknown method')


def token_meta(operation, opt):
    """Generates metadata for a token"""
    meta = {
        'operation': operation,
        'hostname': socket.gethostname()
    }
    if 'USER' in os.environ:
        meta['unix_user'] = os.environ['USER']

    if opt.metadata:
        meta_bits = opt.metadata.split(',')
        for meta_bit in meta_bits:
            key, value = meta_bit.split('=')

        if key not in meta:
            meta[key] = value

    for key, value in meta.items():
        log("Token metadata %s %s" % (key, value), opt)

    return meta


def operational_token(vault_client, operation, opt):
    """Return a properly annotated token for our use."""
    args = {
        'lease': opt.lease,
        'display_name': 'aomi token',
        'meta': token_meta(operation, opt)
    }
    try:
        token = vault_client.create_token(**args)
    except (hvac.exceptions.InvalidRequest,
            hvac.exceptions.Forbidden) as vault_exception:
        if vault_exception.errors[0] == 'permission denied':
            error_output("Permission denied creating operational token", opt)
        else:
            raise vault_exception

    log("Using lease of %s" % opt.lease, opt)
    return token['auth']['client_token']


def client(operation, opt):
    """Return a vault client"""
    if 'VAULT_ADDR' not in os.environ:
        raise aomi.exceptions.AomiError('VAULT_ADDR must be defined')

    vault_host = os.environ['VAULT_ADDR']

    ssl_verify = True
    if 'VAULT_SKIP_VERIFY' in os.environ:
        if os.environ['VAULT_SKIP_VERIFY'] == '1':
            log('Skipping SSL Validation!', opt)
            ssl_verify = False

    log("Connecting to %s" % vault_host, opt)
    vault_client = hvac.Client(vault_host, verify=ssl_verify)
    vault_client.token = initial_token(vault_client, opt)
    if not vault_client.is_authenticated():
        raise aomi.exceptions.AomiCredentials('initial token')

    vault_client.token = operational_token(vault_client, operation, opt)
    if not vault_client.is_authenticated():
        raise aomi.exceptions.AomiCredentials('operational token')

    return vault_client


def get_secretfile(opt):
    """Renders, YAMLs, and returns the Secretfile construct"""
    secretfile_path = abspath(opt.secretfile)
    obj = merge_dicts(load_var_files(opt),
                      cli_hash(opt.extra_vars))
    return yaml.load(render(secretfile_path, obj))


def seed_secrets(config, vault_client, opt):
    """Seed our various secrets"""
    for secret in config.get('secrets', []):
        if 'var_file' in secret:
            aomi.seed.var_file(vault_client, secret, opt)
        elif 'aws_file' in secret:
            aomi.seed.aws(vault_client, secret, opt)
        elif 'files' in secret:
            aomi.seed.files(vault_client, secret, opt)
        elif 'generated' in secret:
            aomi.seed.generated(vault_client, secret['generated'], opt)
        else:
            raise aomi.exceptions.AomiData("secret element %s" % secret)


def seed(vault_client, opt):
    """Will provision vault based on the definition within a Secretfile"""
    config = get_secretfile(opt)
    seed_secrets(config, vault_client, opt)

    for policy in config.get('policies', []):
        aomi.seed.policy(vault_client, policy, opt)

    for app in config.get('apps', []):
        aomi.seed.app(vault_client, app, opt)

    for user in config.get('users', []):
        aomi.seed.users(vault_client, user, opt)

    for audit_log in config.get('audit_logs', []):
        aomi.seed.audit_logs(vault_client, audit_log, opt)

    for approle in config.get('approles', []):
        aomi.seed.approle(vault_client, approle, opt)

    for mount in config.get('mounts', []):
        aomi.seed.mount_path(vault_client, mount, opt)

    for duo in config.get('duo', []):
        aomi.seed.duo(vault_client, duo, opt)
