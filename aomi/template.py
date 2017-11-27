""" Render our templates """
from __future__ import print_function
import os
import sys
import logging
import traceback
import json
from pkg_resources import resource_listdir, resource_filename
import yaml
from jinja2 import Environment, FileSystemLoader, meta
import jinja2.nodes
import jinja2.exceptions
from cryptorito import portable_b64encode, portable_b64decode, polite_string
from aomi.helpers import merge_dicts, abspath, cli_hash
import aomi.exceptions as aomi_excep
# Python 2/3 compat
from future.utils import iteritems  # pylint: disable=E0401
LOG = logging.getLogger(__name__)


def grok_filter_name(element):
    """Extracts the name, which may be embedded, for a Jinja2
    filter node"""
    if element.name == 'default':
        e_name = None
        if isinstance(element.node, jinja2.nodes.Getattr):
            e_name = element.node.node.name
        else:
            e_name = element.node.name

        return e_name


def grok_for_node(element, default_vars):
    """Properly parses a For loop element"""
    if isinstance(element.iter, jinja2.nodes.Filter):
        if element.iter.name == 'default' \
           and element.iter.node.name not in default_vars:
            default_vars.append(element.iter.node.name)

        default_vars = default_vars + grok_vars(element)

    return default_vars


def grok_if_node(element, default_vars):
    """Properly parses a If element"""
    if isinstance(element.test, jinja2.nodes.Filter) and \
       element.test.name == 'default':
        default_vars.append(element.test.node.name)

    return default_vars + grok_vars(element)


def grok_vars(elements):
    """Returns a list of vars for which the value is being appropriately set
    This currently includes the default filter, for-based iterators,
    and the explicit use of set"""
    default_vars = []
    iterbody = None
    if hasattr(elements, 'body'):
        iterbody = elements.body
    elif hasattr(elements, 'nodes'):
        iterbody = elements.nodes

    for element in iterbody:
        if isinstance(element, jinja2.nodes.Output):
            default_vars = default_vars + grok_vars(element)
        elif isinstance(element, jinja2.nodes.Filter):
            e_name = grok_filter_name(element)
            if e_name not in default_vars:
                default_vars.append(e_name)
        elif isinstance(element, jinja2.nodes.For):
            default_vars = grok_for_node(element, default_vars)
        elif isinstance(element, jinja2.nodes.If):
            default_vars = grok_if_node(element, default_vars)
        elif isinstance(element, jinja2.nodes.Assign):
            default_vars.append(element.target.name)
        elif isinstance(element, jinja2.nodes.FromImport):
            for from_var in element.names:
                default_vars.append(from_var)

    return default_vars


def jinja_env(template_path):
    """Sets up our Jinja environment, loading the few filters we have"""
    fs_loader = FileSystemLoader(os.path.dirname(template_path))
    env = Environment(loader=fs_loader,
                      autoescape=True,
                      trim_blocks=True,
                      lstrip_blocks=True)
    env.filters['b64encode'] = portable_b64encode
    env.filters['b64decode'] = f_b64decode
    return env


def f_b64decode(a_string):
    """Wrapper that ensures only strings are returned
    into templates"""
    return polite_string(portable_b64decode(a_string))


def missing_vars(template_vars, parsed_content, obj):
    """If we find missing variables when rendering a template
    we want to give the user a friendly error"""
    missing = []
    default_vars = grok_vars(parsed_content)
    for var in template_vars:
        if var not in default_vars and var not in obj:
            missing.append(var)

    if missing:
        e_msg = "Missing required variables %s" % \
                ','.join(missing)
        raise aomi_excep.AomiData(e_msg)


def render(filename, obj):
    """Render a template, maybe mixing in extra variables"""
    template_path = abspath(filename)
    env = jinja_env(template_path)
    template_base = os.path.basename(template_path)
    try:
        parsed_content = env.parse(env
                                   .loader
                                   .get_source(env, template_base))
        template_vars = meta.find_undeclared_variables(parsed_content)
        if template_vars:
            missing_vars(template_vars, parsed_content, obj)

        LOG.debug("rendering %s with %s vars",
                  template_path, len(template_vars))
        return env \
            .get_template(template_base) \
            .render(**obj)
    except jinja2.exceptions.TemplateSyntaxError as exception:
        template_trace = traceback.format_tb(sys.exc_info()[2])
        # Different error context depending on whether it is the
        # pre-render variable scan or not
        if exception.filename:
            template_line = template_trace[len(template_trace) - 1]
            raise aomi_excep.Validation("Bad template %s %s" %
                                        (template_line,
                                         str(exception)))

        template_str = ''
        if isinstance(exception.source, tuple):
            # PyLint seems confused about whether or not this is a tuple
            # pylint: disable=locally-disabled, unsubscriptable-object
            template_str = "Embedded Template\n%s" % exception.source[0]

        raise aomi_excep.Validation("Bad template %s" % str(exception),
                                    source=template_str)

    except jinja2.exceptions.UndefinedError as exception:
        template_traces = [x.strip()
                           for x in traceback.format_tb(sys.exc_info()[2])
                           if 'template code' in x]
        raise aomi_excep.Validation("Missing template variable %s" %
                                    ' '.join(template_traces))


def load_vars(opt):
    """Loads variable from cli and var files, passing in cli options
    as a seed (although they can be overwritten!).
    Note, turn this into an object so it's a nicer "cache"."""
    if not hasattr(opt, '_vars_cache'):
        cli_opts = cli_hash(opt.extra_vars)
        setattr(opt, '_vars_cache',
                merge_dicts(load_var_files(opt, cli_opts), cli_opts))

    return getattr(opt, '_vars_cache')


def load_var_files(opt, p_obj=None):
    """Load variable files, merge, return contents"""
    obj = {}
    if p_obj:
        obj = p_obj

    for var_file in opt.extra_vars_file:
        LOG.debug("loading vars from %s", var_file)
        obj = merge_dicts(obj.copy(), load_var_file(var_file, obj))

    return obj


def load_var_file(filename, obj):
    """Loads a varible file, processing it as a template"""
    rendered = render(filename, obj)
    ext = os.path.splitext(filename)[1][1:]
    v_obj = dict()
    if ext == 'json':
        v_obj = json.loads(rendered)
    elif ext == 'yaml' or ext == 'yml':
        v_obj = yaml.safe_load(rendered)
    else:
        LOG.warning("assuming yaml for unrecognized extension %s",
                    ext)
        v_obj = yaml.safe_load(rendered)

    return v_obj


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
    LOG.debug("Using Secretfile %s", opt.secretfile)
    secretfile_path = abspath(opt.secretfile)
    obj = load_vars(opt)
    return render(secretfile_path, obj)
