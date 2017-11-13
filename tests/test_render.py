import sys
import unittest
from aomi.render import secret_key_name, cli_hash, grok_template_file
from aomi.cli import parser_factory


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
        args = parser_factory([op] + args)[1]
        return args

    def test_default(self):
        args = self.getopt('environment', ['foo'])
        assert secret_key_name('foo', 'baz', args) == 'foo_baz'

    def test_prefix(self):
        args = self.getopt('environment', ['foo', '--add-prefix',
                                           'zoom',])
        assert secret_key_name('foo', 'baz', args) == 'zoomfoo_baz'
        args = self.getopt('environment', ['foo', '--add-prefix',
                                           'zoom',
                                           '--no-merge-path'])
        assert secret_key_name('foo', 'baz', args) == 'zoombaz'
        args = self.getopt('environment', ['foo', '--add-prefix',
                                           'zoom',
                                           '--add-suffix',
                                           'mooz',
                                           '--no-merge-path'])
        assert secret_key_name('foo', 'baz', args) == 'zoombazmooz'


    def test_suffix(self):
        opt = self.getopt('environment', ['foo', '--add-suffix',
                                          'mooz'])
        assert secret_key_name('foo', 'baz', opt) == 'foo_bazmooz'
        opt = self.getopt('environment', ['foo', '--add-suffix',
                                          'mooz',
                                          '--no-merge-path'])
        assert secret_key_name('foo', 'baz', opt) == 'bazmooz'
        opt = self.getopt('environment', ['foo', '--add-prefix',
                                          'zoom',
                                          '--add-suffix',
                                          'mooz'])
        assert secret_key_name('foo', 'baz', opt) == 'zoomfoo_bazmooz'
