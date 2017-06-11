""" The CLI interface for aomi """
from __future__ import print_function
import os
import sys
from argparse import ArgumentParser
import aomi.vault
import aomi.render
import aomi.template
import aomi.validation
import aomi.util
import aomi.filez
import aomi.seed_action
from aomi.helpers import VERSION as version
from aomi.helpers import log
from aomi.util import token_file, appid_file
from aomi.error import unhandled


def help_me(parser, opt):
    """Handle display of help and whatever diagnostics"""
    print("aomi v%s" % version)
    print('Get started with aomi'
          ' https://autodesk.github.io/aomi/quickstart')
    if opt.verbose:
        tf_str = 'Token File,' if token_file() else ''
        app_str = 'AppID File,' if appid_file() else ''
        tfe_str = 'Token Env,' if 'VAULT_TOKEN' in os.environ else ''
        appre_str = 'App Role Env,' if 'VAULT_ROLE_ID' in os.environ and \
                    'VAULT_SECRET_ID' in os.environ else ''
        appe_str = 'AppID Env,' if 'VAULT_USER_ID' in os.environ and \
                   'VAULT_APP_ID' in os.environ else ''

        log(("Auth Hints Present : %s%s%s%s%s" %
             (tf_str, app_str, tfe_str, appre_str, appe_str))[:-1], opt)
        log("Vault Server %s" %
            os.environ['VAULT_ADDR']
            if 'VAULT_ADDR' in os.environ else '??', opt)

    parser.print_help()
    sys.exit(0)


def extract_file_args(subparsers):
    """Add the command line options for the extract_file operation"""
    extract_parser = subparsers.add_parser('extract_file',
                                           help='Extract a single secret from'
                                           'Vault to a local file')
    extract_parser.add_argument('vault_path',
                                help='Full path (including key) to secret')
    extract_parser.add_argument('destination',
                                help='Location of destination file')
    base_args(extract_parser)


def mapping_args(parser):
    """Add various variable mapping command line options to the parser"""
    parser.add_argument('--add-prefix',
                        dest='add_prefix',
                        help='Specify a prefix to use when '
                        'generating secret key names')
    parser.add_argument('--add-suffix',
                        dest='add_suffix',
                        help='Specify a suffix to use when '
                        'generating secret key names')
    parser.add_argument('--merge-path',
                        dest='merge_path',
                        action='store_true',
                        default=True,
                        help='merge vault path and key name')
    parser.add_argument('--no-merge-path',
                        dest='merge_path',
                        action='store_false',
                        default=True,
                        help='do not merge vault path and key name')
    parser.add_argument('--key-map',
                        dest='key_map',
                        action='append',
                        type=str,
                        default=[])


def export_arg(parser):
    """Add the export argument to a parser"""
    parser.add_argument('--export',
                        dest='export',
                        help='Export declared variables',
                        action='store_true')


def aws_env_args(subparsers):
    """Add command line options for the aws_environment operation"""
    env_parser = subparsers.add_parser('aws_environment')
    env_parser.add_argument('vault_path',
                            help='Full path(s) to the AWS secret')
    export_arg(env_parser)
    base_args(env_parser)


def environment_args(subparsers):
    """Add command line options for the environment operation"""
    env_parser = subparsers.add_parser('environment')
    env_parser.add_argument('vault_paths',
                            help='Full path(s) to secret',
                            nargs='+')
    env_parser.add_argument('--prefix',
                            dest='prefix',
                            help='Old style prefix to use when'
                            'generating secret key names')
    export_arg(env_parser)
    mapping_args(env_parser)
    base_args(env_parser)


def template_args(subparsers):
    """Add command line options for the template operation"""
    template_parser = subparsers.add_parser('template')
    template_parser.add_argument('template',
                                 help='Template source',
                                 nargs='?')
    template_parser.add_argument('destination',
                                 help='Path to write rendered template',
                                 nargs='?')
    template_parser.add_argument('vault_paths',
                                 help='Full path(s) to secret',
                                 nargs='*')
    template_parser.add_argument('--builtin-list',
                                 dest='builtin_list',
                                 help='Display a list of builtin templates',
                                 action='store_true',
                                 default=False)
    template_parser.add_argument('--builtin-info',
                                 dest='builtin_info',
                                 help='Display information on a '
                                 'particular builtin template')
    vars_args(template_parser)
    mapping_args(template_parser)
    base_args(template_parser)


def secretfile_args(parser):
    """Add Secretfile management command line arguments to parser"""
    parser.add_argument('--secrets',
                        dest='secrets',
                        help='Path where secrets are stored',
                        default=os.path.join(os.getcwd(), ".secrets"))
    parser.add_argument('--policies',
                        dest='policies',
                        help='Path where policies are stored',
                        default=os.path.join(os.getcwd(), "vault", ""))
    parser.add_argument('--secretfile',
                        dest='secretfile',
                        help='Secretfile to use',
                        default=os.path.join(os.getcwd(), "Secretfile"))
    parser.add_argument('--tags',
                        dest='tags',
                        help='Tags of things to seed',
                        default=[],
                        type=str,
                        action='append')
    parser.add_argument('--include',
                        dest='include',
                        help='Specify paths to include',
                        default=[],
                        type=str,
                        action='append')
    parser.add_argument('--exclude',
                        dest='exclude',
                        help='Specify paths to exclude',
                        default=[],
                        type=str,
                        action='append')


def generic_args(parser):
    """Command line options associated with every operation
    not just the ones which require connecting to a Vault"""
    parser.add_argument('--verbose',
                        dest='verbose',
                        help='Verbose output',
                        action='store_true')


def base_args(parser):
    """Add the generic command line options"""
    generic_args(parser)
    parser.add_argument('--metadata',
                        dest='metadata',
                        help='A series of key=value pairs for token metadata.',
                        default='')
    parser.add_argument('--lease',
                        dest='lease',
                        help='Lease time for intermediary token.',
                        default='10s')
    parser.add_argument('--reuse-token',
                        dest='reuse_token',
                        help='Whether to reuse the existing token. Note'
                        ' this will cause metadata to not be preserved',
                        action='store_true')


def seed_args(subparsers):
    """Add command line options for the seed operation"""
    seed_parser = subparsers.add_parser('seed')
    secretfile_args(seed_parser)
    vars_args(seed_parser)
    seed_parser.add_argument('--mount-only',
                             dest='mount_only',
                             help='Only mount paths if needed',
                             default=False,
                             action='store_true')
    seed_parser.add_argument('--thaw-from',
                             dest='thaw_from',
                             help='Thaw an ICE file containing secrets')
    base_args(seed_parser)


def archive_args(parser):
    """Add the command line options for archive related operations"""
    parser.add_argument('icefile',
                        help='Path to the encrypted archive'
                        'file of frozen secrets')


def thaw_args(subparsers):
    """Add command line options for the thaw operation"""
    thaw_parser = subparsers.add_parser('thaw')
    secretfile_args(thaw_parser)
    archive_args(thaw_parser)
    vars_args(thaw_parser)
    base_args(thaw_parser)


def freeze_args(subparsers):
    """Add command line options for the freeze operation"""
    freeze_parser = subparsers.add_parser('freeze')
    secretfile_args(freeze_parser)
    archive_args(freeze_parser)
    vars_args(freeze_parser)
    base_args(freeze_parser)


def password_args(subparsers):
    """Add command line options for the set_password operation"""
    password_parser = subparsers.add_parser('set_password')
    password_parser.add_argument('vault_path',
                                 help='Path which contains password'
                                 'secret to be udpated')
    base_args(password_parser)


def help_args(subparsers):
    """Add command line options for the help operation"""
    help_parser = subparsers.add_parser('help')
    generic_args(help_parser)


def vars_args(parser):
    """Add various command line options for external vars"""
    parser.add_argument('--extra-vars',
                        dest='extra_vars',
                        help='Extra template variables',
                        default=[],
                        type=str,
                        action='append')
    parser.add_argument('--extra-vars-file',
                        dest='extra_vars_file',
                        help='YAML files full of variables',
                        default=[],
                        type=str,
                        action='append')


def token_args(subparsers):
    """Add the CLI options for the token operation"""
    token_parser = subparsers.add_parser('token')
    base_args(token_parser)


def parser_factory(fake_args=None):
    """Return a proper contextual OptionParser"""
    parser = ArgumentParser(description='aomi')
    subparsers = parser.add_subparsers(dest='operation',
                                       help='Specify the data '
                                       ' or extraction operation')
    extract_file_args(subparsers)
    environment_args(subparsers)
    aws_env_args(subparsers)
    seed_args(subparsers)
    freeze_args(subparsers)
    thaw_args(subparsers)
    template_args(subparsers)
    password_args(subparsers)
    token_args(subparsers)
    help_args(subparsers)

    if fake_args is None:
        return parser, parser.parse_args()

    return parser, parser.parse_args(fake_args)


def template_runner(client, parser, args):
    """Executes template related operations"""
    if args.builtin_list:
        aomi.template.builtin_list()
    elif args.builtin_info:
        aomi.template.builtin_info(args.builtin_info)
    elif args.template and args.destination and args.vault_paths:
        aomi.render.template(client, args.template,
                             args.destination,
                             args.vault_paths,
                             args)
    else:
        parser.print_usage()
        sys.exit(2)

    sys.exit(0)


def action_runner(parser, args):
    """Run appropriate action, or throw help"""

    if args.operation == 'help':
        help_me(parser, args)

    client = aomi.vault.client(args.operation, args)
    if args.operation == 'extract_file':
        aomi.render.raw_file(client, args.vault_path, args.destination, args)
        sys.exit(0)
    elif args.operation == 'environment':
        aomi.render.env(client, args.vault_paths, args)
        sys.exit(0)
    elif args.operation == 'aws_environment':
        aomi.render.aws(client, args.vault_path, args)
        sys.exit(0)
    elif args.operation == 'seed':
        aomi.validation.gitignore(args)
        aomi.seed_action.seed(client, args)
        sys.exit(0)
    elif args.operation == 'template':
        template_runner(client, parser, args)
    elif args.operation == 'token':
        print(client.token)
        sys.exit(0)
    elif args.operation == 'set_password':
        aomi.util.password(client, args.vault_path, args)
        sys.exit(0)
    elif args.operation == 'freeze':
        aomi.filez.freeze(args.icefile, args)
        sys.exit(0)
    elif args.operation == 'thaw':
        aomi.filez.thaw(args.icefile, args)
        sys.exit(0)

    parser.print_usage()
    sys.exit(2)


def main():
    """Entrypoint, sweet Entrypoint"""
    parser, args = parser_factory()
    try:
        action_runner(parser, args)

    # this is our uncaught handler so yes we want to actually
    # catch every error. the format may vary based on the error handler tho
    except Exception as uncaught:  # pylint: disable=broad-except
        unhandled(uncaught, args)
        sys.exit(1)
