import unittest
import aomi.seed
import aomi.cli

class GeneratedSecretTest(unittest.TestCase):
    def test_secretfile_overwrite(self):
        aomi_opt = aomi.cli.parser_factory(['seed'])[1]
        og_obj = {
            'mount': 'foo',
            'path': 'bar',
            'keys': [
                {
                    'name': 'user',
                    'method': 'words',
                    'overwrite': False
                },
                {
                    'name': 'pass',
                    'method': 'words',
                    'overwrite': True
                }
            ]
        }
        secret = aomi.seed.generate_obj('foo/bar', og_obj, {}, aomi_opt)
        secret2 = aomi.seed.generate_obj('foo/bar', og_obj, secret, aomi_opt)
        assert secret['user'] == secret2['user']
        assert secret['pass'] != secret2['pass']
