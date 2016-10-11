""" Render our templates """
import sys
import os
from base64 import b64encode, b64decode
import yaml
from jinja2 import Environment, FileSystemLoader
from aomi.helpers import merge_dicts


def render(filename, obj):
    """Render a template, maybe mixing in extra variables"""
    template_path = os.path.abspath(filename)
    fs_loader = FileSystemLoader(os.path.dirname(template_path))
    env = Environment(loader=fs_loader)
    env.filters['b64encode'] = portable_b64encode
    env.filters['b64decode'] = portable_b64decode
    template_src = env.get_template(os.path.basename(template_path))
    output = template_src.render(**obj)
    return output


def portable_b64encode(thing):
    """Wrap b64encode for Python 2 & 3"""
    if sys.version_info >= (3, 0):
        return b64encode(bytes(thing, 'utf-8')).decode('utf-8')
    else:
        return b64encode(thing)


def portable_b64decode(thing):
    """Consistent b64decode in Python 2 & 3"""
    if sys.version_info >= (3, 0):
        return b64decode(thing).decode('utf-8')
    else:
        return b64decode(thing)


def load_var_files(opt):
    """Load variable files, merge, return contents"""
    obj = {}
    for var_file in opt.extra_vars_file:
        yamlz = yaml.load(open(os.path.abspath(var_file)).read())
        obj = merge_dicts(obj.copy(), yamlz)

    return obj
