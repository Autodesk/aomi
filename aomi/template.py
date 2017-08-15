""" Render our templates """
from __future__ import print_function
import os
import sys
import traceback
from pkg_resources import resource_listdir, resource_filename
import yaml
from jinja2 import Environment, FileSystemLoader, meta
import jinja2.nodes
import jinja2.exceptions
from cryptorito import portable_b64encode, portable_b64decode
from aomi.helpers import merge_dicts, abspath, cli_hash
import aomi.exceptions as aomi_excep
# Python 2/3 compat
from future.utils import iteritems  # pylint: disable=E0401


def grok_default_vars(parsed_content):
    """Returns a list of vars for which there is a default being set"""
    default_vars = []
    for element in parsed_content.body:
        if isinstance(element, jinja2.nodes.Output):
            for node in element.nodes:
                if isinstance(node, jinja2.nodes.Filter):
                    if node.name == 'default' \
                       and node.node.name not in default_vars:
                        default_vars.append(node.node.name)
        elif isinstance(element, jinja2.nodes.For):
            if isinstance(element.iter, jinja2.nodes.Filter):
                if element.iter.name == 'default' \
                   and element.iter.node.name not in default_vars:
                    default_vars.append(element.iter.node.name)

    return default_vars


def render(filename, obj):
    """Render a template, maybe mixing in extra variables"""
    template_path = abspath(filename)
    fs_loader = FileSystemLoader(os.path.dirname(template_path))
    env = Environment(loader=fs_loader,
                      autoescape=True,
                      trim_blocks=True,
                      lstrip_blocks=True)
    env.filters['b64encode'] = portable_b64encode
    env.filters['b64decode'] = portable_b64decode
    parsed_content = env.parse(env
                               .loader
                               .get_source(env,
                                           os.path.basename(template_path)))

    template_vars = meta.find_undeclared_variables(parsed_content)
    if template_vars:
        missing_vars = []
        default_vars = grok_default_vars(parsed_content)
        for var in template_vars:
            if var not in default_vars and var not in obj:
                missing_vars.append(var)

        if missing_vars:
            e_msg = "Missing required variables %s" % ','.join(missing_vars)
            raise aomi_excep.AomiData(e_msg)

    try:
        return env \
                 .get_template(os.path.basename(template_path)) \
                 .render(**obj)
    except jinja2.exceptions.TemplateSyntaxError as exception:
        template_trace = traceback.format_tb(sys.exc_info()[2])
        raise aomi_excep.Validation("Bad template %s %s" %
                                    (template_trace[len(template_trace) - 1],
                                     str(exception)))
    except jinja2.exceptions.UndefinedError as exception:
        template_traces = [x.strip()
                           for x in traceback.format_tb(sys.exc_info()[2])
                           if 'template code' in x]
        raise aomi_excep.Validation("Missing template variable %s" %
                                    ' '.join(template_traces))


def load_vars(opt):
    """Loads variable from cli and var files, passing in cli options
    as a seed (although they can be overwritten!)"""
    cli_opts = cli_hash(opt.extra_vars)
    return merge_dicts(load_var_files(opt, cli_opts), cli_opts)


def load_var_files(opt, p_obj=None):
    """Load variable files, merge, return contents"""
    obj = {}
    if p_obj:
        obj = p_obj

    for var_file in opt.extra_vars_file:
        yamlz = yaml.safe_load(render(var_file, obj))
        obj = merge_dicts(obj.copy(), yamlz)

    return obj


def load_template_help(builtin):
    """Loads the help for a given template"""

    help_file = "templates/%s-help.yml" % builtin
    help_file = resource_filename(__name__, help_file)
    help_obj = {}
    if os.path.exists(help_file):
        help_data = yaml.safe_load(open(help_file))
        if 'name' in help_data:
            help_obj['name'] = help_data['name']

        if 'help' in help_data:
            help_obj['help'] = help_data['help']

        if 'args' in help_data:
            help_obj['args'] = help_data['args']

    return help_obj


def builtin_list():
    """Show a listing of all our builtin templates"""
    for template in resource_listdir(__name__, "templates"):
        builtin, ext = os.path.splitext(os.path.basename(abspath(template)))
        if ext == '.yml':
            continue

        help_obj = load_template_help(builtin)
        if 'name' in help_obj:
            print("%-*s %s" % (20, builtin, help_obj['name']))
        else:
            print("%s" % builtin)


def builtin_info(builtin):
    """Show information on a particular builtin template"""
    help_obj = load_template_help(builtin)
    if help_obj.get('name') and help_obj.get('help'):
        print("The %s template" % (help_obj['name']))
        print(help_obj['help'])
    else:
        print("No help for %s" % builtin)

    if help_obj.get('args'):
        for arg, arg_help in iteritems(help_obj['args']):
            print("  %-*s %s" % (20, arg, arg_help))


def get_secretfile(opt):
    """Returns the de-YAML'd rendered Secretfile"""
    return yaml.safe_load(render_secretfile(opt))


def render_secretfile(opt):
    """Renders and returns the Secretfile construct"""
    secretfile_path = abspath(opt.secretfile)
    obj = load_vars(opt)
    return render(secretfile_path, obj)
