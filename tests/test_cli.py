import unittest
import aomi.cli

class OpParserTest(unittest.TestCase):
    def test_secretfile(self):
        self.assertTrue(aomi.cli.parser_factory('seed').
                        has_option('--secretfile'))
        self.assertFalse(aomi.cli.parser_factory('environment').
                         has_option('--secretfile'))


    def test_policies(self):
        self.assertTrue(aomi.cli.parser_factory('seed').
                        has_option('--policies'))
        self.assertFalse(aomi.cli.parser_factory('environment').
                         has_option('--policies'))


    def test_secrets(self):
        self.assertTrue(aomi.cli.parser_factory('seed').
                        has_option('--secrets'))
        self.assertFalse(aomi.cli.parser_factory('environment').
                         has_option('--secrets'))


    def test_prefix(self):
        self.assertTrue(aomi.cli.parser_factory('environment').
                        has_option('--prefix'))
        self.assertFalse(aomi.cli.parser_factory('seed').
                         has_option('--prefix'))
