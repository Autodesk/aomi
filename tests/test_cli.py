import unittest
import aomi.cli
                        
class OpParserTest(unittest.TestCase):
    def enabled_options(self, operations, option):
        for op in operations:
            self.assertTrue(aomi.cli.parser_factory(op).has_option(option))

    def disabled_options(self, operations, option):
        for op in operations:
            self.assertFalse(aomi.cli.parser_factory(op).has_option(option))

    def test_secretfile(self):
        self.enabled_options(['seed'], '--secretfile')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'template'], '--secretfile')


    def test_policies(self):
        self.enabled_options(['seed'], '--policies')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'template'], '--policies')


    def test_secrets(self):
        self.enabled_options(['seed'], '--secrets')
        self.disabled_options(['environment',
                               'extract_file',
                               'aws_environment',
                               'template'], '--secrets')


    def test_prefix(self):
        self.enabled_options(['environment'], '--prefix')
        self.disabled_options(['seed',
                               'extract_file',
                               'aws_environment',
                               'template'], '--prefix')

    def test_verbose(self):
        self.enabled_options(['environment',
                              'seed',
                              'extract_file',
                              'aws_environment',
                              'template'], '--verbose')
