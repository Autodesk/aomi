import sys
import unittest
from aomi.render import secret_key_name, cli_hash, grok_template_file, is_aws, grok_seconds
from aomi.cli import parser_factory


class HelperTest(unittest.TestCase):
    def test_seconds_to_seconds(self):
        assert grok_seconds('1s') == 1
        assert grok_seconds('60s') == 60
        assert grok_seconds('120s') == 120

    def test_minutes_to_seconds(self):
        assert grok_seconds('1m') == 60
        assert grok_seconds('60m') == 3600

    def test_hours_to_seconds(self):
        assert grok_seconds('1h') == 3600
        assert grok_seconds('24h') == 86400

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
