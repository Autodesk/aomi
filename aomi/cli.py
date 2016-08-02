""" The CLI interface for aomi """
from __future__ import print_function
import os
import sys

from optparse import OptionParser
import aomi.vault
import aomi.render


def usage():
    """Real Time Help"""
    print('aomi extract_file <vault path> <file path>')
    print('aomi environment <vault path>')
    print('aomi aws_environment <vault path>')
    print('aomi seed [--secretfile ./Secretfile]'
          ' [--secrets ./secrets] [--policies ./vault]')
    print('aomi template <template> <destination> <path>')


def parser_factory(operation):
    """Return a proper contextual OptionParser"""
    parser = OptionParser()

    parser.add_option('--verbose',
                      dest='verbose',
                      help='Verbose output',
                      action='store_true')

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
    elif operation == 'environment':
        parser.add_option('--prefix',
                          dest='prefix',
                          help='Specify a prefix to use when '
                          'generating environment variables')

    return parser


def action_runner(operation, client):
    """Run appropriate action, or throw help"""
    parser = parser_factory(operation)

    (opt, args) = parser.parse_args()

    if operation == 'help':
        usage()
        sys.exit(0)
    elif operation == 'extract_file':
        if len(args) == 3:
            aomi.render.raw_file(client, args[1], args[2])
            sys.exit(0)
    elif operation == 'environment':
        if len(args) == 2:
            aomi.render.env(client, args[1], opt)
            sys.exit(0)
    elif operation == 'aws_environment':
        if len(args) == 2:
            aomi.render.aws(client, args[1])
            sys.exit(0)
    elif operation == 'seed':
        if len(args) == 1:
            aomi.vault.seed(client, opt)
            sys.exit(0)
    elif operation == 'template':
        if len(args) == 4:
            aomi.render.template(client, args[1], args[2], args[3])
            sys.exit(0)
    usage()
    sys.exit(1)


def main():
    """Entrypoint, sweet Entrypoint"""
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    operation = sys.argv[1]
    client = aomi.vault.client()
    action_runner(operation, client)
