import sys
import unittest
from aomi.render import secret_key_name, cli_hash, grok_template_file, is_aws, grok_seconds
from aomi.cli import parser_factory


class HelperTest(unittest.TestCase):
    def test_is_aws(self):
        assert is_aws({'access_key': True, 'secret_key': True})
        assert is_aws({'access_key': True, 'secret_key': True, 'security_token': True})

    def test_is_not_aws(self):
        assert not is_aws({'aaa': True})

class TemplateTest(unittest.TestCase):
    def test_builtin(self):
        builtin_file = grok_template_file('builtin:foo')
        assert builtin_file.endswith('foo.j2')
        assert not builtin_file.startswith('builtin:')

    def test_normal(self):
        builtin_file = grok_template_file('/foo')
        assert builtin_file == '/foo'

class SecretKeyNameTest(unittest.TestCase):
    def getopt(self, op, args):
        old_sysargv = sys.argv
        sys.argv = [op] + args
        (opt, args) = parser_factory(op).parse_args()
        sys.argv = old_sysargv
        return opt

    def test_default(self):
        opt = self.getopt('environment', [])
        assert secret_key_name('foo', 'baz', opt) == 'foo_baz'

    def test_prefix(self):
        opt = self.getopt('environment', ['--add-prefix',
                                          'zoom'])
        assert secret_key_name('foo', 'baz', opt) == 'zoomfoo_baz'
        opt = self.getopt('environment', ['--add-prefix',
                                          'zoom',
                                          '--no-merge-path'])
        assert secret_key_name('foo', 'baz', opt) == 'zoombaz'
        opt = self.getopt('environment', ['--add-prefix',
                                          'zoom',
                                          '--add-suffix',
                                          'mooz',
                                          '--no-merge-path'])
        assert secret_key_name('foo', 'baz', opt) == 'zoombazmooz'


    def test_suffix(self):
        opt = self.getopt('environment', ['--add-suffix',
                                          'mooz'])
        assert secret_key_name('foo', 'baz', opt) == 'foo_bazmooz'
        opt = self.getopt('environment', ['--add-suffix',
                                          'mooz',
                                          '--no-merge-path'])
        assert secret_key_name('foo', 'baz', opt) == 'bazmooz'
        opt = self.getopt('environment', ['--add-prefix',
                                          'zoom',
                                          '--add-suffix',
                                          'mooz'])
        assert secret_key_name('foo', 'baz', opt) == 'zoomfoo_bazmooz'
