""" Vault interactions """
from __future__ import print_function
import os
import socket
import logging
import hvac
import yaml
from aomi.error import output as error_output
from aomi.util import token_file, appid_file
import aomi.error
import aomi.exceptions
LOG = logging.getLogger(__name__)


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


def initial_token(vault_client):
    """Generate our first token based on workstation configuration"""

    app_filename = appid_file()
    token_filename = token_file()
    if 'VAULT_TOKEN' in os.environ and os.environ['VAULT_TOKEN']:
        LOG.info('Token derived from VAULT_TOKEN environment variable')
        return os.environ['VAULT_TOKEN'].strip()
    elif 'VAULT_USER_ID' in os.environ and \
         'VAULT_APP_ID' in os.environ and \
         os.environ['VAULT_USER_ID'] and os.environ['VAULT_APP_ID']:
        token = app_token(vault_client,
                          os.environ['VAULT_APP_ID'].strip(),
                          os.environ['VAULT_USER_ID'].strip())
        LOG.info("Token derived from VAULT_APP_ID and VAULT_USER_ID")
        return token
    elif 'VAULT_ROLE_ID' in os.environ and \
         'VAULT_SECRET_ID' in os.environ and \
         os.environ['VAULT_ROLE_ID'] and os.environ['VAULT_SECRET_ID']:
        token = approle_token(vault_client,
                              os.environ['VAULT_ROLE_ID'],
                              os.environ['VAULT_SECRET_ID'])
        LOG.info("Token derived from VAULT_ROLE_ID and VAULT_SECRET_ID")
        return token
    elif app_filename:
        token = yaml.safe_load(open(app_filename).read().strip())
        if 'app_id' in token and 'user_id' in token:
            token = app_token(vault_client,
                              token['app_id'],
                              token['user_id'])
            LOG.info("Token derived from %s", app_filename)
            return token
    elif token_filename:
        LOG.info("Token derived from %s", token_filename)
        return open(token_filename, 'r').read().strip()
    else:
        raise aomi.exceptions.AomiCredentials('unknown method')


def token_meta(operation, opt):
    """Generates metadata for a token"""
    meta = {
        'via': 'aomi',
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
        LOG.debug("Token metadata %s %s", key, value)

    return meta


def operational_token(vault_client, operation, opt):
    """Return a properly annotated token for our use. This
    token will be revoked at the end of the session. The token
    will have some decent amounts of metadata tho."""
    display_name = vault_client.lookup_token()['data']['display_name']
    args = {
        'lease': opt.lease,
        'display_name': display_name,
        'meta': token_meta(operation, opt)
    }
    try:
        token = vault_client.create_token(**args)
    except (hvac.exceptions.InvalidRequest,
            hvac.exceptions.Forbidden) as vault_exception:
        if vault_exception.errors[0] == 'permission denied':
            error_output("Permission denied creating operational token", opt)
        else:
            raise

    LOG.debug("Using lease of %s", opt.lease)
    return token['auth']['client_token']


def client(operation, opt):
    """Return a vault client"""
    if 'VAULT_ADDR' not in os.environ:
        raise aomi.exceptions.AomiError('VAULT_ADDR must be defined')

    vault_host = os.environ['VAULT_ADDR']

    ssl_verify = True
    if 'VAULT_SKIP_VERIFY' in os.environ:
        if os.environ['VAULT_SKIP_VERIFY'] == '1':
            LOG.warn('Skipping SSL Validation!')
            ssl_verify = False

    LOG.info("Connecting to %s", vault_host)
    vault_client = hvac.Client(vault_host, verify=ssl_verify)
    vault_client.token = initial_token(vault_client)
    if not vault_client.is_authenticated():
        raise aomi.exceptions.AomiCredentials('initial token')

    if opt.reuse_token:
        LOG.debug("Not creating operational token")
    else:
        vault_client.token = operational_token(vault_client, operation, opt)
        if not vault_client.is_authenticated():
            raise aomi.exceptions.AomiCredentials('operational token')

    return vault_client


def is_mounted(backend, path, backends):
    """Determine whether a backend of a certain type is mounted"""
    for mount_name, values in backends.items():
        b_norm = '/'.join([x for x in mount_name.split('/') if x])
        m_norm = '/'.join([x for x in path.split('/') if x])
        if (m_norm == b_norm) and values['type'] == backend:
            return True

    return False


def wrap_hvac(msg):
    """Error catching Vault API wrapper
    This decorator wraps API interactions with Vault. It will
    catch and return appropriate error output on common
    problems"""
    # pylint: disable=missing-docstring
    def wrap_call(func):
        # pylint: disable=missing-docstring
        def func_wrapper(self, vault_client):
            try:
                return func(self, vault_client)
            except (hvac.exceptions.InvalidRequest,
                    hvac.exceptions.Forbidden) as vault_exception:
                if vault_exception.errors[0] == 'permission denied':
                    error_output("Permission denied %s from %s" %
                                 (msg, self.path), self.opt)
                else:
                    raise

        return func_wrapper
    return wrap_call
