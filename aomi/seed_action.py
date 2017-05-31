""" The aomi "seed" loop """
from __future__ import print_function
import os
from shutil import rmtree
import tempfile
# need to override those SSL warnings
from aomi.filez import thaw
from aomi.model import Context
import aomi.error
import aomi.exceptions


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

    ctx = Context.load(opt)
    ctx.fetch(vault_client, opt)
    ctx.sync(vault_client, opt)

    if opt.thaw_from:
        rmtree(opt.secrets)
