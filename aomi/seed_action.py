""" The aomi "seed" loop """
from __future__ import print_function
import os
from shutil import rmtree
import tempfile
# need to override those SSL warnings
import aomi.seed
from aomi.filez import thaw
from aomi.vault import get_secretfile
import aomi.error
import aomi.exceptions


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


def auto_thaw(opt):
    """Will thaw into a temporary location"""
    icefile = opt.thaw_from
    if not os.path.exists(icefile):
        raise aomi.exceptions.IceFile("%s missing" % icefile)

    thaw(icefile, opt)
    return opt


def seed(vault_client, opt):
    """Will provision vault based on the definition within a Secretfile"""
    if opt.thaw_from:
        opt.secrets = tempfile.mkdtemp('aomi-thaw')
        auto_thaw(opt)

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

    if opt.thaw_from:
        rmtree(opt.secrets)
