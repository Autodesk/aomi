"""Wrappers for GPG/Keybase functionality we need"""
from __future__ import print_function
import os
import json
from tempfile import mkstemp
import subprocess
import requests
from aomi.helpers import problems, flatten, log


def massage_key(key):
    """Massage the keybase return for only what we care about"""
    return {
        'fingerprint': key['key_fingerprint'],
        'bundle': key['bundle']
    }


def key_from_keybase(username):
    """Look up a public key from a username"""
    url = "https://keybase.io/_/api/1.0/user/lookup.json?usernames=%s" \
          % username
    resp = requests.get(url)
    if resp.status_code == 200:
        j_resp = json.loads(resp.content)
        if 'them' in j_resp and len(j_resp['them']) == 1 \
           and 'public_keys' in j_resp['them'][0] \
           and 'pgp_public_keys' in j_resp['them'][0]['public_keys']:
            key = j_resp['them'][0]['public_keys']['primary']
            return massage_key(key)

    return None


def has_gpg_key(fingerprint):
    """Checks to see if we have this gpg fingerprint"""
    if len(fingerprint) > 8:
        fingerprint = fingerprint[-8:]

    fingerprint = fingerprint.upper()
    cmd = flatten(["/usr/local/bin/gpg", gnupg_home(), "--list-public-keys"])
    keys = subprocess.check_output(cmd)
    lines = keys.split('\n')
    pub_keys = [line for line in lines if line.startswith('pub')]
    return len([key for key in pub_keys if key.find(fingerprint) > -1]) == 1


def import_gpg_key(key):
    """Imports a GPG key"""
    key_fd, key_filename = mkstemp("aomi-gpg-import")
    key_handle = os.fdopen(key_fd, 'w')
    key_handle.write(key)
    key_handle.close()
    cmd = ["/usr/local/bin/gpg", gnupg_home(), "--import", key_filename],
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    msg = 'gpg: Total number processed: 1'
    return len([line for line in output.split('\n') if line == msg]) == 1


def passphrase_file():
    """Read passphrase from a file. This should only ever be
    used by our built in integration tests."""
    if 'AOMI_PASSPHRASE_FILE' in os.environ:
        return ["--batch", "--passphrase-file",
                os.environ['AOMI_PASSPHRASE_FILE']]
    else:
        return []


def gnupg_home():
    """Returns appropriate arguments if GNUPGHOME is set"""
    if 'GNUPGHOME' in os.environ:
        return ["--homedir", os.environ['GNUPGHOME']]
    else:
        return []


def encrypt(source, dest, keys, opt):
    """Encrypts a file using the given keys"""
    recipients = [["--recipient", key.encode('ASCII')] for key in keys]
    cmd = list(flatten(["/usr/local/bin/gpg", "--armor", "--output", dest,
                        gnupg_home(), passphrase_file(), recipients,
                        "--encrypt", source]))
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, exception:
        log("GPG Command %s" % ' '.join(exception.cmd), opt)
        log("GPG Output %s" % exception.output, opt)
        problems("Unable to GPG")

    return True


def decrypt(source, dest):
    """Attempts to decrypt a file"""
    cmd = flatten(["/usr/local/bin/gpg", "--output", dest, "--decrypt",
                   gnupg_home(), passphrase_file(), source])
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    return True
