""" Vault interactions """
from __future__ import print_function
import os
import socket
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hvac
import yaml
from aomi.helpers import normalize_vault_path
from aomi.util import token_file, appid_file, approle_file
from aomi.validation import sanitize_mount
import aomi.error
import aomi.exceptions
LOG = logging.getLogger(__name__)


def is_aws(data):
    """Takes a decent guess as to whether or not we are dealing with
    an AWS secret blob"""
    return 'access_key' in data and 'secret_key' in data


def grok_seconds(lease):
    """Ensures that we are returning just seconds"""
    if lease.endswith('s'):
        return int(lease[0:-1])
    elif lease.endswith('m'):
        return int(lease[0:-1]) * 60
    elif lease.endswith('h'):
        return int(lease[0:-1]) * 3600

    return None


def renew_secret(client, creds, opt):
    """Renews a secret. This will occur unless the user has
    specified on the command line that it is not neccesary"""
    if opt.reuse_token:
        return

    seconds = grok_seconds(opt.lease)
    if not seconds:
        raise aomi.exceptions.AomiCommand("invalid lease %s" % opt.lease)

    renew = None
    if client.version:
        v_bits = client.version.split('.')
        if int(v_bits[0]) == 0 and \
           int(v_bits[1]) <= 8 and \
           int(v_bits[2]) <= 0:
            r_obj = {
                'increment': seconds
            }
            r_path = "v1/sys/renew/{0}".format(creds['lease_id'])
            # Pending discussion on https://github.com/ianunruh/hvac/issues/148
            # pylint: disable=protected-access
            renew = client._post(r_path, json=r_obj).json()

    if not renew:
        renew = client.renew_secret(creds['lease_id'], seconds)

    # sometimes it takes a bit for vault to respond
    # if we are within 5s then we are fine
    if not renew or (seconds - renew['lease_duration'] >= 5):
        client.revoke_self_token()
        e_msg = 'Unable to renew with desired lease'
        raise aomi.exceptions.VaultConstraint(e_msg)


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
    problems. Do we even need this now that we extend the
    hvac class?"""
    # pylint: disable=missing-docstring
    def wrap_call(func):
        # pylint: disable=missing-docstring
        def func_wrapper(self, vault_client):
            try:
                return func(self, vault_client)
            except (hvac.exceptions.InvalidRequest,
                    hvac.exceptions.Forbidden) as vault_exception:
                if vault_exception.errors[0] == 'permission denied':
                    emsg = "Permission denied %s from %s" % (msg, self.path)
                    raise aomi.exceptions.AomiCredentials(emsg)
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
        self.version = None
        self.vault_addr = os.environ.get('VAULT_ADDR')
        if not self.vault_addr:
            raise aomi.exceptions.AomiError('VAULT_ADDR is undefined or empty')

        if not self.vault_addr.startswith("http"):
            raise aomi.exceptions.AomiError('VAULT_ADDR must be a URL')

        ssl_verify = True
        if 'VAULT_SKIP_VERIFY' in os.environ:
            if os.environ['VAULT_SKIP_VERIFY'] == '1':
                import urllib3
                urllib3.disable_warnings()
                ssl_verify = False

        self.initial_token = None
        self.operational_token = None
        session = requests.Session()
        retries = Retry(total=5,
                        backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        super(Client, self).__init__(url=self.vault_addr,
                                     verify=ssl_verify,
                                     session=session)

    def server_version(self):
        """Attempts to determine the version of Vault that a
        server is running. Some actions will change on older
        Vault deployments."""
        health_url = "%s/v1/sys/health" % self.vault_addr
        resp = self.session.request('get', health_url, **self._kwargs)
        if resp.status_code == 200 or resp.status_code == 429:
            blob = resp.json()
            if 'version' in blob:
                return blob['version']
        else:
            raise aomi.exceptions.VaultProblem('Health check failed')

        return None

    def connect(self, opt):
        """This sets up the tokens we expect to see in a way
        that hvac also expects."""
        if not self._kwargs['verify']:
            LOG.warning('Skipping SSL Validation!')

        self.version = self.server_version()
        self.token = self.init_token()
        my_token = self.lookup_token()
        if not my_token or 'data' not in my_token:
            raise aomi.exceptions.AomiCredentials('initial token')

        display_name = my_token['data']['display_name']
        vsn_string = ""
        if self.version:
            vsn_string = ", v%s" % self.version
        else:
            LOG.warning("Unable to deterine Vault version. Not all "
                        "functionality is supported")

        LOG.info("Connected to %s as %s%s",
                 self._url,
                 display_name,
                 vsn_string)

        if opt.reuse_token:
            LOG.debug("Not creating operational token")
            self.initial_token = self.token
            self.operational_token = self.token
        else:
            self.initial_token = self.token
            self.operational_token = self.op_token(display_name, opt)
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
            LOG.debug("Token derived from VAULT_ROLE_ID and VAULT_SECRET_ID")
            return token
        elif 'VAULT_TOKEN' in os.environ and os.environ['VAULT_TOKEN']:
            LOG.debug('Token derived from VAULT_TOKEN environment variable')
            return os.environ['VAULT_TOKEN'].strip()
        elif 'VAULT_USER_ID' in os.environ and \
             'VAULT_APP_ID' in os.environ and \
             os.environ['VAULT_USER_ID'] and os.environ['VAULT_APP_ID']:
            token = app_token(self,
                              os.environ['VAULT_APP_ID'].strip(),
                              os.environ['VAULT_USER_ID'].strip())
            LOG.debug("Token derived from VAULT_APP_ID and VAULT_USER_ID")
            return token
        elif approle_filename:
            creds = yaml.safe_load(open(approle_filename).read().strip())
            if 'role_id' in creds and 'secret_id' in creds:
                token = approle_token(self,
                                      creds['role_id'],
                                      creds['secret_id'])
                LOG.debug("Token derived from approle file")
                return token
        elif token_filename:
            LOG.debug("Token derived from %s", token_filename)
            try:
                return open(token_filename, 'r').read().strip()
            except IOError as os_exception:
                if os_exception.errno == 21:
                    raise aomi.exceptions.AomiFile('Bad Vault token file')

                raise
        elif app_filename:
            token = yaml.safe_load(open(app_filename).read().strip())
            if 'app_id' in token and 'user_id' in token:
                token = app_token(self,
                                  token['app_id'],
                                  token['user_id'])
                LOG.debug("Token derived from %s", app_filename)
                return token
        else:
            raise aomi.exceptions.AomiCredentials('unknown method')

    def op_token(self, display_name, opt):
        """Return a properly annotated token for our use. This
        token will be revoked at the end of the session. The token
        will have some decent amounts of metadata tho."""
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
                emsg = "Permission denied creating operational token"
                raise aomi.exceptions.AomiCredentials(emsg)
            else:
                raise

        LOG.debug("Created operational token with lease of %s", opt.lease)
        return token['auth']['client_token']

    def read(self, path, wrap_ttl=None):
        """Wrap the hvac read call, using the right token for
        cubbyhole interactions."""
        path = sanitize_mount(path)
        if path.startswith('cubbyhole'):
            self.token = self.initial_token
            val = super(Client, self).read(path, wrap_ttl)
            self.token = self.operational_token
            return val

        return super(Client, self).read(path, wrap_ttl)

    def write(self, path, wrap_ttl=None, **kwargs):
        """Wrap the hvac write call, using the right token for
        cubbyhole interactions."""
        path = sanitize_mount(path)
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
        path = sanitize_mount(path)
        if path.startswith('cubbyhole'):
            self.token = self.initial_token
            val = super(Client, self).delete(path)
            self.token = self.operational_token
            return val
        else:
            super(Client, self).delete(path)
