""" Vault interactions """
from __future__ import print_function
import os
import socket
import logging
import hvac
import yaml
from aomi.helpers import normalize_vault_path
from aomi.error import output as error_output
from aomi.util import token_file, appid_file, approle_file
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


def token_meta(opt):
    """Generates metadata for a token"""
    meta = {
        'via': 'aomi',
        'operation': opt.operation,
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


def is_mounted(backend, path, backends):
    """Determine whether a backend of a certain type is mounted"""
    for mount_name, values in backends.items():
        b_norm = normalize_vault_path(mount_name)
        m_norm = normalize_vault_path(path)
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


class Client(hvac.Client):
    """Our Vault Client Wrapper
    This class will pass the existing hvac bits through. When interacting
    with cubbyhole paths, it will use the non operational token in order
    to preserve access."""
    # dat hvac tho
    # pylint: disable=too-many-arguments
    def __init__(self, _url=None, token=None, _cert=None, _verify=True,
                 _timeout=30, _proxies=None, _allow_redirects=True,
                 _session=None):
        vault_addr = os.environ.get('VAULT_ADDR')
        if not vault_addr:
            raise aomi.exceptions.AomiError('VAULT_ADDR is undefined or empty')

        ssl_verify = True
        if 'VAULT_SKIP_VERIFY' in os.environ:
            if os.environ['VAULT_SKIP_VERIFY'] == '1':
                ssl_verify = False

        self.initial_token = None
        self.operational_token = None
        super(Client, self).__init__(url=vault_addr,
                                     verify=ssl_verify)

    def connect(self, opt):
        """This sets up the tokens we expect to see in a way
        that hvac also expects."""
        LOG.info("Connecting to %s", self._url)
        if not self._kwargs['verify']:
            LOG.warning('Skipping SSL Validation!')

        self.token = self.init_token()
        if not self.is_authenticated():
            raise aomi.exceptions.AomiCredentials('initial token')

        if opt.reuse_token:
            LOG.debug("Not creating operational token")
            self.initial_token = self.token
            self.operational_token = self.token
        else:
            self.initial_token = self.token
            self.operational_token = self.op_token(opt)
            if not self.is_authenticated():
                raise aomi.exceptions.AomiCredentials('operational token')

            self.token = self.operational_token

        return self

    def init_token(self):
        """Generate our first token based on workstation configuration"""

        app_filename = appid_file()
        token_filename = token_file()
        approle_filename = approle_file()
        if 'VAULT_ROLE_ID' in os.environ and \
           'VAULT_SECRET_ID' in os.environ and \
           os.environ['VAULT_ROLE_ID'] and os.environ['VAULT_SECRET_ID']:
            token = approle_token(self,
                                  os.environ['VAULT_ROLE_ID'],
                                  os.environ['VAULT_SECRET_ID'])
            LOG.info("Token derived from VAULT_ROLE_ID and VAULT_SECRET_ID")
            return token
        elif 'VAULT_TOKEN' in os.environ and os.environ['VAULT_TOKEN']:
            LOG.info('Token derived from VAULT_TOKEN environment variable')
            return os.environ['VAULT_TOKEN'].strip()
        elif 'VAULT_USER_ID' in os.environ and \
             'VAULT_APP_ID' in os.environ and \
             os.environ['VAULT_USER_ID'] and os.environ['VAULT_APP_ID']:
            token = app_token(self,
                              os.environ['VAULT_APP_ID'].strip(),
                              os.environ['VAULT_USER_ID'].strip())
            LOG.info("Token derived from VAULT_APP_ID and VAULT_USER_ID")
            return token
        elif approle_filename:
            creds = yaml.safe_load(open(approle_filename).read().strip())
            if 'role_id' in creds and 'secret_id' in creds:
                token = approle_token(self,
                                      creds['role_id'],
                                      creds['secret_id'])
                LOG.info("Token derived from approle file")
                return token
        elif token_filename:
            LOG.info("Token derived from %s", token_filename)
            return open(token_filename, 'r').read().strip()
        elif app_filename:
            token = yaml.safe_load(open(app_filename).read().strip())
            if 'app_id' in token and 'user_id' in token:
                token = app_token(self,
                                  token['app_id'],
                                  token['user_id'])
                LOG.info("Token derived from %s", app_filename)
                return token
        else:
            raise aomi.exceptions.AomiCredentials('unknown method')

    def op_token(self, opt):
        """Return a properly annotated token for our use. This
        token will be revoked at the end of the session. The token
        will have some decent amounts of metadata tho."""
        display_name = self.lookup_token()['data']['display_name']
        args = {
            'lease': opt.lease,
            'display_name': display_name,
            'meta': token_meta(opt)
        }
        try:
            token = self.create_token(**args)
        except (hvac.exceptions.InvalidRequest,
                hvac.exceptions.Forbidden) as vault_exception:
            if vault_exception.errors[0] == 'permission denied':
                error_output("Permission denied creating operational token",
                             opt)
            else:
                raise

        LOG.debug("Using lease of %s", opt.lease)
        return token['auth']['client_token']

    def read(self, path, wrap_ttl=None):
        """Wrap the hvac read call, using the right token for
        cubbyhole interactions."""
        if path.startswith('cubbyhole'):
            self.token = self.initial_token
            val = super(Client, self).read(path, wrap_ttl)
            self.token = self.operational_token
            return val

        return super(Client, self).read(path, wrap_ttl)

    def write(self, path, wrap_ttl=None, **kwargs):
        """Wrap the hvac write call, using the right token for
        cubbyhole interactions."""
        if path.startswith('cubbyhole'):
            self.token = self.initial_token
            val = super(Client, self).write(path, wrap_ttl=wrap_ttl, **kwargs)
            self.token = self.operational_token
            return val
        else:
            super(Client, self).write(path, wrap_ttl=wrap_ttl, **kwargs)

    def delete(self, path):
        """Wrap the hvac delete call, using the right token for
        cubbyhole interactions."""
        if path.startswith('cubbyhole'):
            self.token = self.initial_token
            val = super(Client, self).delete(path)
            self.token = self.operational_token
            return val
        else:
            super(Client, self).delete(path)
