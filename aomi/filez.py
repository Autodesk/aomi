"""Handle various kinds of import/export of secrets"""
from __future__ import print_function
import os
import shutil
import time
import logging
import datetime
import zipfile
from cryptorito import key_from_keybase, has_gpg_key, \
    import_gpg_key, encrypt, decrypt

from aomi.helpers import subdir_path, ensure_dir, ensure_tmpdir
from aomi.template import get_secretfile
from aomi.validation import gpg_fingerprint \
    as validate_gpg_fingerprint
import aomi.exceptions
from aomi.model import Context
LOG = logging.getLogger(__name__)


def from_keybase(username):
    """Will attempt to retrieve a GPG public key from
    Keybase, importing if neccesary"""
    public_key = key_from_keybase(username)
    fingerprint = public_key['fingerprint'][-8:].upper().encode('ascii')
    key = public_key['bundle'].encode('ascii')
    if not has_gpg_key(fingerprint):
        LOG.debug("Importing gpg key for %s", username)
        if not import_gpg_key(key):
            raise aomi.exceptions.KeybaseAPI("import key for %s" % username)

    return fingerprint


def grok_keys(config):
    """Will retrieve a GPG key from either Keybase or GPG directly"""
    key_ids = []
    for key in config['pgp_keys']:
        if key.startswith('keybase:'):
            key_id = from_keybase(key[8:])
            LOG.debug("Encrypting for keybase user %s", key[8:])
        else:
            if not has_gpg_key(key):
                raise aomi.exceptions.GPG("Do not actually have key %s" % key)

            LOG.debug("Encrypting for gpg id %s", key)
            key_id = key

        validate_gpg_fingerprint(key_id)
        key_ids.append(key_id)

    return key_ids


def freeze_archive(tmp_dir, dest_prefix):
    """Generates a ZIP file of secrets"""
    zip_filename = "%s/aomi-blah.zip" % tmp_dir
    archive = zipfile.ZipFile(zip_filename, 'w')
    for root, _dirnames, filenames in os.walk(dest_prefix):
        for filename in filenames:
            relative_path = subdir_path(root, dest_prefix).split(os.sep)[1:]
            relative_path = os.sep.join(relative_path)
            archive.write("%s/%s" % (root, filename),
                          "%s/%s" % (relative_path, filename))

    archive.close()
    return zip_filename


def freeze_encrypt(dest_dir, zip_filename, config, opt):
    """Encrypts the zip file"""
    pgp_keys = grok_keys(config)
    icefile_prefix = "aomi-%s" % \
                     os.path.basename(os.path.dirname(opt.secretfile))
    if opt.icefile_prefix:
        icefile_prefix = opt.icefile_prefix

    timestamp = time.strftime("%H%M%S-%m-%d-%Y",
                              datetime.datetime.now().timetuple())
    ice_file = "%s/%s-%s.ice" % (dest_dir, icefile_prefix, timestamp)
    if not encrypt(zip_filename, ice_file, pgp_keys):
        raise aomi.exceptions.GPG("Unable to encrypt zipfile")

    return ice_file


def freeze(dest_dir, opt):
    """Iterates over the Secretfile looking for secrets to freeze"""
    tmp_dir = ensure_tmpdir()
    dest_prefix = "%s/dest" % tmp_dir
    ensure_dir(dest_dir)
    ensure_dir(dest_prefix)
    config = get_secretfile(opt)
    Context.load(config, opt) \
           .freeze(dest_prefix)
    zip_filename = freeze_archive(tmp_dir, dest_prefix)
    ice_file = freeze_encrypt(dest_dir, zip_filename, config, opt)
    shutil.rmtree(tmp_dir)
    LOG.debug("Generated file is %s", ice_file)


def thaw_decrypt(vault_client, src_file, tmp_dir, opt):
    """Decrypts the encrypted ice file"""

    if not os.path.isdir(opt.secrets):
        LOG.info("Creating secret directory %s", opt.secrets)
        os.mkdir(opt.secrets)

    zip_file = "%s/aomi.zip" % tmp_dir

    if opt.gpg_pass_path:
        gpg_path_bits = opt.gpg_pass_path.split('/')
        gpg_path = '/'.join(gpg_path_bits[0:len(gpg_path_bits) - 1])
        gpg_field = gpg_path_bits[len(gpg_path_bits) - 1]
        resp = vault_client.read(gpg_path)
        gpg_pass = None
        if resp and 'data' in resp and gpg_field in resp['data']:
            gpg_pass = resp['data'][gpg_field]
            if not gpg_pass:
                raise aomi.exceptions.GPG("Unable to retrieve GPG password")

            LOG.debug("Retrieved GPG password from Vault")
            if not decrypt(src_file, zip_file, passphrase=gpg_pass):
                raise aomi.exceptions.GPG("Unable to gpg")

        else:
            raise aomi.exceptions.VaultData("Unable to retrieve GPG password")
    else:
        if not decrypt(src_file, zip_file):
            raise aomi.exceptions.GPG("Unable to gpg")

    return zip_file


def thaw(vault_client, src_file, opt):
    """Given the combination of a Secretfile and the output of
    a freeze operation, will restore secrets to usable locations"""
    if not os.path.exists(src_file):
        raise aomi.exceptions.AomiFile("%s does not exist" % src_file)

    tmp_dir = ensure_tmpdir()
    zip_file = thaw_decrypt(vault_client, src_file, tmp_dir, opt)
    archive = zipfile.ZipFile(zip_file, 'r')
    for archive_file in archive.namelist():
        archive.extract(archive_file, tmp_dir)
        os.chmod("%s/%s" % (tmp_dir, archive_file), 0o640)
        LOG.debug("Extracted %s from archive", archive_file)

    LOG.info("Thawing secrets into %s", opt.secrets)
    config = get_secretfile(opt)
    Context.load(config, opt) \
           .thaw(tmp_dir)
