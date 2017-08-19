""" The aomi "seed" loop """
from __future__ import print_function
import os
import difflib
from shutil import rmtree
import tempfile
from termcolor import colored
import yaml
from future.utils import iteritems  # pylint: disable=E0401
from aomi.helpers import dict_unicodeize
from aomi.filez import thaw
from aomi.model import Context
from aomi.template import get_secretfile, render_secretfile
from aomi.model.resource import CHANGED, ADD, DEL, OVERWRITE, NOOP
from aomi.model.auth import Policy
from aomi.model.aws import AWSRole
from aomi.validation import is_unicode
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

    Context.load(get_secretfile(opt), opt) \
           .fetch(vault_client) \
           .sync(vault_client, opt)

    if opt.thaw_from:
        rmtree(opt.secrets)


def render(directory, opt):
    """Render any provided template. This includes the Secretfile,
    Vault policies, and inline AWS roles"""
    if not os.path.exists(directory) and not os.path.isdir(directory):
        os.mkdir(directory)

    a_secretfile = render_secretfile(opt)
    open("%s/Secretfile" % directory, 'w').write(a_secretfile)
    ctx = Context.load(yaml.safe_load(a_secretfile), opt)
    for resource in ctx.resources():
        if not resource.present:
            continue

        if issubclass(type(resource), Policy):
            if not os.path.isdir("%s/policy" % directory):
                os.mkdir("%s/policy" % directory)
            filename = "%s/policy/%s" % (directory, resource.path)
            open(filename, 'w').write(resource.obj())
        elif issubclass(type(resource), AWSRole):
            if not os.path.isdir("%s/aws" % directory):
                os.mkdir("%s/aws" % directory)
            if 'policy' in resource.obj():
                filename = "%s/aws/%s" % (directory,
                                          os.path.basename(resource.path))
                r_obj = resource.obj()
                if 'policy' in r_obj:
                    open(filename, 'w').write(r_obj['policy'])


def export(vault_client, opt):
    """Export contents of a Secretfile from the Vault server
    into a specified directory."""
    ctx = Context.load(get_secretfile(opt), opt) \
                 .fetch(vault_client)
    for resource in ctx.resources():
        resource.export(opt.directory)


def maybe_colored(msg, color, opt):
    """Maybe it will render in color maybe it will not!"""
    if opt.monochrome:
        return msg

    return colored(msg, color)


def normalize_val(val):
    """Normalize JSON/YAML derived values as they pertain
    to Vault resources and comparison operations """
    if is_unicode(val) and val.isdigit():
        return int(val)
    elif isinstance(val, list):
        return ','.join(val)
    elif val is None:
        return ''

    return val


def details_dict(resource, opt):
    """Output the changes, if any, for a dict"""
    existing = dict_unicodeize(resource.existing)
    obj = dict_unicodeize(resource.obj())
    for ex_k, ex_v in iteritems(existing):
        new_value = normalize_val(obj.get(ex_k))
        og_value = normalize_val(ex_v)
        if ex_k in obj and og_value != new_value:
            print(maybe_colored("%s: %s" % (ex_k, og_value),
                                'red', opt))
            print(maybe_colored("%s: %s" % (ex_k, new_value),
                                'green', opt))

        if ex_k not in obj:
            print(maybe_colored("%s: %s" % (ex_k, og_value),
                                'red', opt))

    for ob_k, ob_v in iteritems(obj):
        val = normalize_val(ob_v)
        if ob_k not in existing:
            print(maybe_colored("%s: %s" % (ob_k, val),
                                'green', opt))

    return


def maybe_details(resource, opt):
    """At the first level of verbosity this will print out detailed
    change information on for the specified Vault resource"""

    if opt.verbose == 0:
        return

    if not resource.present:
        return

    obj = resource.obj()
    if not obj:
        return

    if is_unicode(resource.existing) and is_unicode(obj):
        a_diff = difflib.unified_diff(resource.existing.splitlines(),
                                      obj.splitlines(),
                                      lineterm="")
        for line in a_diff:
            if line.startswith('+++') or line.startswith('---'):
                continue
            if line[0] == '+':
                print(maybe_colored(line, 'green', opt))
            elif line[0] == '-':
                print(maybe_colored(line, 'red', opt))
            else:
                print(line)
    elif isinstance(resource.existing, dict):
        details_dict(resource, opt)


def diff(vault_client, opt):
    """Derive a comparison between what is represented in the Secretfile
    and what is actually live on a Vault instance"""
    if opt.thaw_from:
        opt.secrets = tempfile.mkdtemp('aomi-thaw')
        auto_thaw(opt)
    ctx = Context.load(get_secretfile(opt), opt) \
                 .fetch(vault_client)

    for resource in ctx.resources():
        changed = resource.diff()
        if changed == ADD:
            print("%s %s" % (maybe_colored("+", "green", opt), str(resource)))
        elif changed == DEL:
            print("%s %s" % (maybe_colored("-", "red", opt), str(resource)))
        elif changed == CHANGED:
            print("%s %s" % (maybe_colored("~", "yellow", opt), str(resource)))
        elif changed == OVERWRITE:
            print("%s %s" % (maybe_colored("+", "yellow", opt), str(resource)))

        if changed != OVERWRITE and changed != NOOP:
            maybe_details(resource, opt)

    if opt.thaw_from:
        rmtree(opt.secrets)
