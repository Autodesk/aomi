""" Vault interactions """
from __future__ import print_function
import os
import hvac
import yaml
# need to override those SSL warnings
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from aomi.helpers import problems, log
import aomi.seed

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def app_token(vault_client, app_id, user_id):
    """Returns a vault token based on the app and user id."""
    resp = vault_client.auth_app_id(app_id, user_id)
    if 'auth' in resp and 'client_token' in resp['auth']:
        return resp['auth']['client_token']
    else:
        problems('Unable to retrieve app token')


def client():
    """Return a vault client"""
    if 'VAULT_ADDR' not in os.environ:
        problems('VAULT_ADDR must be defined')

    ssl_verify = True
    if 'VAULT_SKIP_VERIFY' in os.environ:
        if os.environ['VAULT_SKIP_VERIFY'] == '1':
            ssl_verify = False

    token_file = os.environ.get('VAULT_TOKEN_FILE',
                                "%s/.vault-token" % os.environ['HOME'])
    app_file = os.environ.get('AOMI_APP_FILE',
                              "%s/.aomi-app-token" % os.environ['HOME'])
    token_file = os.path.abspath(token_file)
    app_file = os.path.abspath(app_file)

    vault_client = hvac.Client(os.environ['VAULT_ADDR'], verify=ssl_verify)
    if 'VAULT_TOKEN' in os.environ and len(os.environ['VAULT_TOKEN']) > 0:
        vault_client.token = os.environ['VAULT_TOKEN'].strip()
    elif 'VAULT_USER_ID' in os.environ and \
         'VAULT_APP_ID' in os.environ and \
         len(os.environ['VAULT_USER_ID']) > 0 and \
         len(os.environ['VAULT_APP_ID']) > 0:
        vault_client.token = app_token(vault_client,
                                       os.environ['VAULT_APP_ID'].strip(),
                                       os.environ['VAULT_USER_ID'].strip())

        return client
    elif os.path.exists(app_file):
        token = yaml.load(open(app_file).read().strip())
        if 'app_id' in token and 'user_id' in token:
            vault_client.token = app_token(vault_client,
                                           token['app_id'],
                                           token['user_id'])
        return vault_client
    elif os.path.exists(token_file):
        vault_client.token = open(token_file, 'r').read().strip()
    else:
        problems('Unable to determine vault authentication method')

    if not vault_client.is_authenticated():
        problems("Unable to authenticate with vault")

    return vault_client


def seed(vault_client, opt):
    """Will provision vault based on the definition within a Secretfile"""
    config = yaml.load(open(os.path.abspath(opt.secretfile)).read())
    for secret in config.get('secrets', []):
        if 'var_file' in secret:
            aomi.seed.var_file(vault_client, secret, opt)
        elif 'aws_file' in secret:
            aomi.seed.aws(vault_client, secret, opt)
        elif 'files' in secret:
            aomi.seed.files(vault_client, secret, opt)
        else:
            problems("Invalid secret element %s" % secret)

    for app in config.get('apps', []):
        if 'app_file' in app:
            aomi.seed.app(vault_client, app, opt)
        else:
            problems("Invalid app element %s" % app)
