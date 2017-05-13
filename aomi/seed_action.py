""" The aomi "seed" loop """
from __future__ import print_function
import sys
import inspect
import os
from shutil import rmtree
import tempfile
from future.utils import iteritems  # pylint: disable=E0401
# need to override those SSL warnings
from aomi.filez import thaw
from aomi.template import get_secretfile
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


def py_resources():
    """Discovers all aomi Vault resource models"""
    aomi_mods = [m for
                 m, _v in iteritems(sys.modules)
                 if m.startswith('aomi.model')]
    mod_list = []
    mod_map = []
    for amod in [sys.modules[m] for m in aomi_mods]:
        for _mod_bit, model in inspect.getmembers(amod):
            if str(model) in mod_list:
                continue

            if model == aomi.model.Mount:
                mod_list.append(str(model))
                mod_map.append((model.config_key, model))
            elif (inspect.isclass(model) and
                  issubclass(model, aomi.model.Resource) and
                  model.config_key):
                mod_list.append(str(model))
                if model.resource_key:
                    mod_map.append((model.config_key,
                                    model.resource_key,
                                    model))
                elif model.config_key != 'secrets':
                    mod_map.append((model.config_key, model))

    return mod_map


def find_model(config, obj, mods):
    """Given a list of mods (as returned by py_resources) attempts to
    determine if a given Python obj fits one of the models"""
    for mod in mods:
        if mod[0] != config:
            continue

        if len(mod) == 2:
            return mod[1]

        if len(mod) == 3 and mod[1] in obj:
            return mod[2]

    return None


def seed(vault_client, opt):
    """Will provision vault based on the definition within a Secretfile"""
    if opt.thaw_from:
        opt.secrets = tempfile.mkdtemp('aomi-thaw')
        auto_thaw(opt)

    config = get_secretfile(opt)
    ctx = Context()
    seed_map = py_resources()
    seed_keys = set([m[0] for m in seed_map])
    for config_key in seed_keys:
        if config_key not in config:
            continue
        for resource in config[config_key]:
            mod = find_model(config_key, resource, seed_map)
            if not mod:
                print("unable to find mod for %s" % resource)
                continue

            ctx.add(mod(resource, opt))

    for config_key in config.keys():
        if config_key not in seed_keys:
            print("missing model for %s" % config_key)

    f_ctx = aomi.model.filtered_context(ctx, opt)
    f_ctx.fetch(vault_client, opt)
    f_ctx.sync(vault_client, opt)

    if opt.thaw_from:
        rmtree(opt.secrets)
