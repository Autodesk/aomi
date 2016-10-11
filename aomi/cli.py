""" The CLI interface for aomi """
from __future__ import print_function
import os
import sys

from optparse import OptionParser
import aomi.vault
import aomi.render
import aomi.validation
from aomi.helpers import VERSION as version


def usage():
    """Real Time Help"""
    print("aomi version (%s)" % version)
    print('aomi extract_file <vault path> <file path>')
    print('aomi environment <vault path>')
    print('aomi aws_environment <vault path>')
    print('aomi seed [--secretfile ./Secretfile]'
          ' [--secrets ./secrets] [--policies ./vault]')
    print('aomi template <template> <destination> <path>')
    print('aomi token')


def parser_factory(operation):
    """Return a proper contextual OptionParser"""
    parser = OptionParser()

    parser.add_option('--verbose',
                      dest='verbose',
                      help='Verbose output',
                      action='store_true')
    parser.add_option('--metadata',
                      dest='metadata',
                      help='A series of key=value pairs for token metadata.',
                      default='')
    parser.add_option('--lease',
                      dest='lease',
                      help='Lease time for intermediary token.',
                      default='10s')

    if operation == 'seed':
        parser.add_option('--secrets',
                          dest='secrets',
                          help='Path where secrets are stored',
                          default="%s/.secrets" % os.getcwd())
        parser.add_option('--policies',
                          dest='policies',
                          help='Path where policies are stored',
                          default="%s/vault" % os.getcwd())
        parser.add_option('--secretfile',
                          dest='secretfile',
                          help='Secretfile to use',
                          default="%s/Secretfile" % os.getcwd())
        parser.add_option('--tags',
                          dest='tags',
                          help='Tags of things to seed',
                          default=[],
                          type=str,
                          action='append')
        parser.add_option('--mount-only',
                          dest='mount_only',
                          help='Only mount paths if needed',
                          default=False,
                          action='store_true')
    elif operation == 'environment' or operation == 'template':
        parser.add_option('--add-prefix',
                          dest='add_prefix',
                          help='Specify a prefix to use when '
                          'generating secret key names')
        parser.add_option('--add-suffix',
                          dest='add_suffix',
                          help='Specify a suffix to use when '
                          'generating secret key names')
        parser.add_option('--merge-path',
                          dest='merge_path',
                          action='store_true',
                          default=True,
                          help='merge vault path and key name')
        parser.add_option('--no-merge-path',
                          dest='merge_path',
                          action='store_false',
                          default=True,
                          help='do not merge vault path and key name')
        parser.add_option('--key-map',
                          dest='key_map',
                          action='append',
                          type=str,
                          default=[])

    if operation == 'template' or operation == 'seed':
        parser.add_option('--extra-vars',
                          dest='extra_vars',
                          help='Extra template variables',
                          default=[],
                          type=str,
                          action='append')
        parser.add_option('--extra-vars-file',
                          dest='extra_vars_file',
                          help='YAML files full of variables',
                          default=[],
                          type=str,
                          action='append')

    if operation == 'environment' or operation == 'aws_environment':
        parser.add_option('--export',
                          dest='export',
                          help='Export declared variables',
                          action='store_true')

    if operation == 'environment':
        parser.add_option('--prefix',
                          dest='prefix',
                          help='Old style prefix to use when '
                          'generating secret key names')

    return parser


def parse_extra_vars(extra_vars):
    """Parse out a hash from a list of key=value strings"""
    ev_obj = {}
    for ev in extra_vars:
        key, val = ev.split('=')
        ev_obj[key] = val

    return ev_obj


def action_runner(operation):
    """Run appropriate action, or throw help"""

    parser = parser_factory(operation)
    (opt, args) = parser.parse_args()
    if operation == 'help':
        usage()
        sys.exit(0)

    client = aomi.vault.client(operation, opt)
    if operation == 'extract_file':
        if len(args) == 3:
            aomi.render.raw_file(client, args[1], args[2])
            sys.exit(0)
    elif operation == 'environment':
        if len(args) >= 2:
            paths = args[1:]
            aomi.render.env(client, paths, opt)
            sys.exit(0)
    elif operation == 'aws_environment':
        if len(args) == 2:
            aomi.render.aws(client, args[1], opt)
            sys.exit(0)
    elif operation == 'seed':
        if len(args) == 1:
            aomi.validation.gitignore(opt)
            aomi.vault.seed(client, opt)
            sys.exit(0)
    elif operation == 'template':
        if len(args) >= 4:
            paths = args[3:]
            aomi.render.template(client, args[1], args[2], paths, opt)
            sys.exit(0)
    elif operation == 'token':
        if len(args) == 1:
            print(client.token)
            sys.exit(0)

    usage()
    sys.exit(1)


def main():
    """Entrypoint, sweet Entrypoint"""
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    operation = sys.argv[1]
    action_runner(operation)
