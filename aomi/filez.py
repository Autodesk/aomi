"""Hande various kinds of import/export of secrets"""
from __future__ import print_function
import os
import tempfile
import shutil
import time
import datetime
import zipfile
import gnupg
from keybase import keybase

from aomi.helpers import problems, warning, hard_path, log, get_password
from aomi.vault import get_secretfile


def haz_key(key, gpg):
    """Will determine if a given key ID is know to our
    local GPG instance"""
    key_ids = [x['keyid'][-8:] for x in gpg.list_keys()]
    return key in key_ids


def from_keybase(username, gpg, opt):
    """Will attempt to retrieve a GPG public key from
    Keybase, importing if neccesary"""
    kbase = keybase.Keybase(username)
    if not kbase:
        problems("Unknown keybase user %s" % username)

    public_key = kbase.get_public_key()
    key = public_key.key_fingerprint[-8:].upper().encode('ascii')
    if not haz_key(key, gpg):
        log("Importing gpg key for %s" % username, opt)
        res = gpg.import_keys(public_key.ascii)
        if not res.results[0]['status'].startswith('Entirely new'):
            problems("Unable to import key for %s" % username)

    return key


def grok_keys(gpg, config, opt):
    """Will retrieve a GPG key from either Keybase or GPG directly"""
    key_ids = []
    for key in config['pgp_keys']:
        if key.startswith('keybase:'):
            key_id = from_keybase(key[8:], gpg, opt)
            log("Encrypting for keybase user %s" % key[8:], opt)
        else:
            if not haz_key(key, gpg):
                problems("Do not actually have key %s" % key)

            log("Encrypting for gpg id %s" % key, opt)
            key_id = key

        key_ids.append(key_id)

    return key_ids


def freeze_secret(src, dest, flav, tmp_dir, opt):
    """Copies a secret into a particular location"""
    src_file = hard_path(src, opt.secrets)
    dest_file = "%s/%s" % (tmp_dir, dest)
    shutil.copyfile(src_file, dest_file)
    log("Froze %s %s" % flav, opt)


def freeze_files(config, tmp_dir, opt):
    """Copy files which are to be frozen to their temporary location"""
    for app in config.get('apps', []):
        freeze_secret(app['app_file'], app['app_file'], 'app', tmp_dir, opt)

    for user in config.get('users', []):
        pfile = user['password_file'],
        freeze_secret(pfile, pfile, 'user', tmp_dir, opt)

    for secret in config.get('secrets', []):
        if 'var_file' in secret:
            sfile = secret['var_file']
            freeze_secret(sfile, sfile, 'var_file', tmp_dir, opt)
        elif 'aws_file' in secret:
            sfile = secret['aws_file']
            freeze_secret(sfile, sfile, 'aws_file', tmp_dir, opt)
        elif 'files' in secret:
            for a_secret in secret['files']:
                sfile = a_secret['source']
                freeze_secret(sfile, sfile, 'file', tmp_dir, opt)


def freeze_archive(tmp_dir, dest_prefix):
    """Generates a ZIP file of secrets"""
    zip_filename = "%s/aomi-blah.zip" % tmp_dir
    archive = zipfile.ZipFile(zip_filename, 'w')
    for archive_file in os.listdir(dest_prefix):
        archive.write("%s/%s" % (dest_prefix, archive_file), archive_file)

    archive.close()
    return zip_filename


def freeze_encrypt(dest_dir, zip_filename, tmp_dir, config, opt):
    """Encrypts the zip file"""
    gpg = gnupg.GPG(homedir="%s/.gnupg" % os.environ['HOME'],
                    binary='/usr/local/bin/gpg')

    pgp_keys = grok_keys(gpg, config, opt)

    handle = open(zip_filename, 'r')
    zip_data = handle.read()
    handle.close()
    shutil.rmtree(tmp_dir)
    ice_handle = os.path.basename(os.path.dirname(opt.secretfile))
    timestamp = time.strftime("%H%M%S-%m-%d-%Y",
                              datetime.datetime.now().timetuple())
    ice_file = "%s/aomi-%s-%s.ice" % (dest_dir, ice_handle, timestamp)
    enc_resp = gpg.encrypt(zip_data,
                           *pgp_keys,
                           output=ice_file)
    if not enc_resp.ok:
        problems("Unable to encrypt zipfile")

    return ice_file


def freeze(dest_dir, opt):
    """Iterates over the Secretfile looking for secrets to freeze"""
    if not (os.path.exists(dest_dir) and
            os.path.isdir(dest_dir)):
        os.mkdir(dest_dir)

    tmp_dir = tempfile.mkdtemp('aomi-freeze')
    dest_prefix = "%s/dest" % tmp_dir
    os.mkdir(dest_prefix)
    config = get_secretfile(opt)

    freeze_files(config, tmp_dir, opt)
    zip_filename = freeze_archive(tmp_dir, dest_prefix)
    ice_file = freeze_encrypt(dest_dir, zip_filename, tmp_dir, config, opt)
    print("Generated file is %s" % ice_file)


def thaw_decrypt(src_file, tmp_dir, opt):
    """Decrypts the encrypted ice file"""
    gpg = gnupg.GPG(homedir="%s/.gnupg" % os.environ['HOME'],
                    binary='/usr/local/bin/gpg')

    if not os.path.isdir(opt.secrets):
        warning("Creating secret directory %s" % opt.secrets)
        os.mkdir(opt.secrets)

    zip_file = "%s/aomi.zip" % tmp_dir,
    ice_handle = open(src_file, 'r')
    resp = gpg.decrypt_file(ice_handle, output=zip_file)
    ice_handle.close()
    if not resp.ok:
        if resp.stderr.find('NEED_PASSPHRASE') != -1:
            log("No keyless gpg keys available, requesting password", opt)
            passphrase = get_password(opt, confirm=False)
            ice_handle = open(src_file, 'r')
            resp = gpg.decrypt_file(ice_handle,
                                    output=zip_file,
                                    passphrase=passphrase)
            ice_handle.close()
        else:
            log("GPG STDERR %s" % resp.stderr, opt)
            problems("Unable to GPG")

    if not resp.ok:
        problems("Unable to decrypt %s" % src_file)

    return zip_file


def thaw_secret(filename, tmp_dir, flav, opt):
    """Will perform some validation and copy a
    decrypted secret to it's final location"""
    src_file = "%s/%s" % (tmp_dir, filename)
    dest_file = "%s/%s" % (opt.secrets, filename)
    if not os.path.exists(src_file):
        problems("%s file %s missing" % (flav, filename))

    shutil.copyfile(src_file, dest_file)
    log("Thawed %s %s" % (flav, filename), opt)


def thaw(src_file, opt):
    """Given the combination of a Secretfile and the output of
    a freeze operation, will restore secrets to usable locations"""
    if not os.path.exists(src_file):
        problems("%s does not exist" % src_file)

    tmp_dir = tempfile.mkdtemp('aomi-freeze')

    zip_file = thaw_decrypt(src_file, tmp_dir, opt)

    archive = zipfile.ZipFile(zip_file, 'r')
    for archive_file in archive.namelist():
        archive.extract(archive_file, tmp_dir)
        log("Extracted %s from archive" % archive_file, opt)

    log("Thawing secrets into %s" % opt.secrets, opt)
    config = get_secretfile(opt)
    for app in config.get('apps', []):
        thaw_secret(app['app_file'], tmp_dir, 'App', opt)

    for user in config.get('users', []):
        thaw_secret(user['password_file'], tmp_dir, 'User', opt)

    for secret in config.get('secrets', []):
        if 'var_file' in secret:
            dest_file = "%s/%s" % (opt.secrets, secret['var_file'])
            var_file = os.path.basename(dest_file)
            src_file = "%s/%s" % (tmp_dir, var_file)
            if not os.path.exists(src_file):
                problems("Var file %s missing" % var_file)

            shutil.copyfile(src_file, dest_file)
            log("Thawed var_file %s" % var_file, opt)
        elif 'aws_file' in secret:
            dest_file = "%s/%s" % (opt.secrets, secret['aws_file'])
            aws_file = os.path.basename(dest_file)
            src_file = "%s/%s" % (tmp_dir, aws_file)
            if not os.path.exists(src_file):
                problems("AWS file %s missing" % var_file)

            shutil.copyfile(src_file, dest_file)
            log("Thawed aws_file %s" % aws_file, opt)
        elif 'files' in secret:
            for a_secret in secret['files']:
                dest_file = "%s/%s" % (opt.secrets, a_secret['source'])
                filename = os.path.basename(dest_file)
                src_file = "%s/%s" % (tmp_dir, filename)
                if not os.path.exists(src_file):
                    problems("File %s missing" % filename)

                shutil.copyfile(src_file, dest_file)
                log("Thawed file %s" % filename, opt)
