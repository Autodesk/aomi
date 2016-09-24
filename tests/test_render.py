import sys
import unittest
from aomi.render import secret_key_name, cli_hash
from aomi.cli import parser_factory

class CliHashTest(unittest.TestCase):
    def test_happy_path(self):
        assert cli_hash(["foo=bar"]) == {'foo': 'bar'}
        assert cli_hash(["foo=bar","baz=bam"]) == {'foo': 'bar', 'baz': 'bam'}


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
