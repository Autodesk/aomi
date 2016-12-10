import unittest
import aomi.cli

class OpParserTest(unittest.TestCase):
    def enabled_options(self, operations, option):
        for op in operations:
            self.assertTrue(aomi.cli.parser_factory(op).has_option(option))

    def disabled_options(self, operations, option):
        for op in operations:
            self.assertFalse(aomi.cli.parser_factory(op).has_option(option))

    def test_secretfile_option(self):
        self.enabled_options(['seed', 'freeze', 'thaw'], '--secretfile')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'template',
                               'set_password',
                               'token'], '--secretfile')


    def test_policies_option(self):
        self.enabled_options(['seed',
                              'thaw',
                              'freeze'], '--policies')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'template',
                               'set_password',
                               'token'], '--policies')


    def test_secrets_option(self):
        self.enabled_options(['seed', 'freeze', 'thaw'], '--secrets')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'template',
                               'set_password',
                               'token'], '--secrets')


    def test_mount_only_option(self):
        self.enabled_options(['seed'], '--mount-only')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'template',
                               'token',
                               'set_password',
                               'freeze',
                               'thaw'], '--mount-only')


    def test_prefix_option(self):
        self.enabled_options(['environment'], '--prefix')
        self.disabled_options(['seed',
                               'aws_environment',
                               'template'
                               'extract_file',
                               'set_password',
                               'freeze',
                               'thaw',
                               'token'], '--prefix')


    def test_prefix_option(self):
        self.enabled_options(['environment',
                              'template'], '--add-prefix')
        self.disabled_options(['seed',
                               'extract_file',
                               'aws_environment',
                               'freeze',
                               'thaw',
                               'set_password',
                               'token'], '--add-prefix')

    def test_suffix_option(self):
        self.enabled_options(['environment',
                              'template'], '--add-suffix')
        self.disabled_options(['seed',
                               'extract_file',
                               'aws_environment',
                               'freeze',
                               'thaw',
                               'set_password',
                               'token'], '--add-suffix')


    def test_merge_path_option(self):
        self.enabled_options(['environment',
                              'template'], '--merge-path')
        self.disabled_options(['seed',
                               'extract_file',
                               'aws_environment',
                               'freeze',
                               'thaw',
                               'set_password',
                               'token'], '--merge-path')


    def test_no_merge_path_option(self):
        self.enabled_options(['environment',
                              'template'], '--no-merge-path')
        self.disabled_options(['seed',
                               'extract_file',
                               'aws_environment',
                               'freeze',
                               'thaw',
                               'set_password',
                               'token'], '--no-merge-path')

    def test_verbose_option(self):
        self.enabled_options(['environment',
                              'seed',
                              'extract_file',
                              'aws_environment',
                              'template'], '--verbose')

    def test_metadata_option(self):
        self.enabled_options(['environment',
                              'seed',
                              'extract_file',
                              'aws_environment',
                              'template',
                              'freeze',
                              'thaw',
                              'set_password',
                              'token'], '--metadata')

    def test_lease_option(self):
        self.enabled_options(['environment',
                              'seed',
                              'extract_file',
                              'aws_environment',
                              'template',
                              'set_password',
                              'token'], '--lease')
        self.disabled_options(['freeze', 'thaw'], '--export')


    def test_export_option(self):
        self.enabled_options(['environment', 'aws_environment'], '--export')
        self.disabled_options(['seed',
                               'extract_file',
                               'template',
                               'set_password',
                               'token',
                               'freeze',
                               'thaw'], '--export')
        
    def test_extra_vars_option(self):
        self.enabled_options(['template',
                              'seed',
                              'freeze',
                              'thaw'], '--extra-vars')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'set_password',
                               'token'], '--extra-vars')

    def test_extra_vars_file_option(self):
        self.enabled_options(['template',
                              'seed',
                              'freeze',
                              'thaw'], '--extra-vars-file')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'set_password',
                               'token'], '--extra-vars-file')
