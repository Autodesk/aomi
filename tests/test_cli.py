import unittest
import aomi.cli

class OpParserTest(unittest.TestCase):
    def enabled_options(self, operations, option):
        for op in operations:
            self.assertTrue(option.replace('-', '_') in aomi.cli.parser_factory(op)[1].__dict__)

    def disabled_options(self, operations, option):
        for op in operations:
            self.assertFalse(option.replace('-', '_') in aomi.cli.parser_factory(op)[1].__dict__)

    def test_secretfile_option(self):
        self.enabled_options([['seed'],
                              ['freeze', 'fake'],
                              ['thaw', 'fake']], 'secretfile')
        self.disabled_options([['environment', 'foo'],
                               ['extract_file', 'foo', 'bar'],
                               ['aws_environment', 'foo'],
                               ['template', 'foo', 'bar', 'baz'],
                               ['set_password', 'foo'],
                               ['token']], 'secretfiles')


    def test_policies_option(self):
        self.enabled_options([['seed'],
                              ['thaw', 'foo'],
                              ['freeze', 'foo']], 'policies')
        self.disabled_options([['environment', 'foo'],
                               ['extract_file', 'foo', 'bar'],
                               ['aws_environment', 'foo'],
                               ['template', 'foo', 'bar', 'baz'],
                               ['set_password', 'foo'],
                               ['token']], 'policies')


    def test_secrets_option(self):
        self.enabled_options([['seed'],
                              ['freeze', 'foo'],
                              ['thaw', 'foo']], 'secrets')
        self.disabled_options([['environment', 'foo'],
                               ['extract_file', 'foo', 'bar'],
                               ['aws_environment', 'foo'],
                               ['template', 'foo', 'bar', 'baz'],
                               ['set_password', 'foo'],
                               ['token']], 'secrets')


    def test_mount_only_option(self):
        self.enabled_options([['seed']], 'mount-only')
        self.disabled_options([['environment', 'foo'],
                               ['extract_file', 'foo', 'bar'],
                               ['aws_environment', 'foo'],
                               ['template', 'foo', 'bar', 'baz'],
                               ['set_password', 'foo'],
                               ['token'],
                               ['freeze', 'foo'],
                               ['thaw', 'foo']], 'mount-only')


    def test_prefix_option(self):
        self.enabled_options([['environment', 'foo']], 'prefix')
        self.disabled_options([['seed'],
                               ['extract_file', 'foo', 'bar'],
                               ['aws_environment', 'foo'],
                               ['template', 'foo', 'bar', 'baz'],
                               ['set_password', 'foo'],
                               ['freeze', 'foo'],
                               ['thaw', 'foo'],
                               ['token']], 'prefix')


    def test_add_prefix_option(self):
        self.enabled_options([['environment', 'foo'],
                              ['template', 'foo', 'bar', 'baz']], 'add-prefix')
        self.disabled_options([['seed'],
                               ['extract_file', 'foo', 'bar'],
                               ['set_password', 'foo'],
                               ['freeze', 'foo'],
                               ['thaw', 'foo'],
                               ['token']], 'add-prefix')

    def test_suffix_option(self):
        self.enabled_options([['environment', 'foo'],
                              ['template', 'foo', 'bar', 'baz']], 'add-suffix')
        self.disabled_options([['seed'],
                               ['extract_file', 'foo', 'bar'],
                               ['set_password', 'foo'],
                               ['freeze', 'foo'],
                               ['thaw', 'foo'],
                               ['token']], 'add-suffix')

    def test_merge_path_option(self):
        self.enabled_options([['environment', 'foo'],
                              ['template', 'foo', 'bar', 'baz']], 'merge-path')
        self.disabled_options([['seed'],
                               ['extract_file', 'foo', 'bar'],
                               ['set_password', 'foo'],
                               ['freeze', 'foo'],
                               ['thaw', 'foo'],
                               ['token']], 'merge-path')


    def test_verbose_option(self):
        self.enabled_options([['environment', 'foo'],
                              ['aws_environment', 'foo'],
                              ['template', 'foo', 'bar', 'baz'],
                              ['seed'],
                              ['extract_file', 'foo', 'bar'],
                              ['set_password', 'foo'],
                              ['freeze', 'foo'],
                              ['thaw', 'foo'],
                              ['token']], 'verbose')

    def test_metadata_option(self):
        self.enabled_options([['environment', 'foo'],
                              ['aws_environment', 'foo'],
                              ['template', 'foo', 'bar', 'baz'],
                              ['seed'],
                              ['extract_file', 'foo', 'bar'],
                              ['set_password', 'foo'],
                              ['freeze', 'foo'],
                              ['thaw', 'foo'],
                              ['token']], 'metadata')

    def test_lease_option(self):
        self.enabled_options([['environment', 'foo'],
                              ['aws_environment', 'foo'],
                              ['template', 'foo', 'bar', 'baz'],
                              ['seed'],
                              ['extract_file', 'foo', 'bar'],
                              ['set_password', 'foo'],
                              ['freeze', 'foo'],
                              ['thaw', 'foo'],
                              ['token']], 'lease')


    def test_export_option(self):
        self.enabled_options([['environment', 'foo'],
                              ['aws_environment', 'foo']], 'export')
        self.disabled_options([['template', 'foo', 'bar', 'baz'],
                               ['seed'],
                               ['extract_file', 'foo', 'bar'],
                               ['set_password', 'foo'],
                               ['freeze', 'foo'],
                               ['thaw', 'foo'],
                               ['token']], 'export')


    def test_extra_vars_option(self):
        self.enabled_options([['template', 'foo', 'bar', 'baz'],
                              ['freeze', 'foo'],
                              ['thaw', 'foo'],
                              ['seed']], 'extra-vars')
        self.disabled_options([['environment', 'foo'],
                               ['aws_environment', 'foo'],
                               ['extract_file', 'foo', 'bar'],
                               ['set_password', 'foo'],
                               ['token']], 'extra-vars')

    def test_extra_vars_file_option(self):
        self.enabled_options([['template', 'foo', 'bar', 'baz'],
                              ['freeze', 'foo'],
                              ['thaw', 'foo'],
                              ['seed']], 'extra-vars-file')
        self.disabled_options([['environment', 'foo'],
                               ['aws_environment', 'foo'],
                               ['extract_file', 'foo', 'bar'],
                               ['set_password', 'foo'],
                               ['token']], 'extra-vars-file')
