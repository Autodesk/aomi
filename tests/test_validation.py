import sys
import unittest
import aomi.validation
from aomi.cli import parser_factory


class VaultPathTest(unittest.TestCase):
    def setUp(self):
        self.args = parser_factory(['seed'])[1]

    def test_happy_path(self):
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.args))
        self.assertTrue(aomi.validation.specific_path_check('foo/bam', self.args))

    def test_include(self):
        self.args.include = ['foo/bar']
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.args))
        self.assertFalse(aomi.validation.specific_path_check('foo/bam', self.args))

    def test_exclude(self):
        self.args.exclude = ['foo/bar']
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.args))
        self.assertTrue(aomi.validation.specific_path_check('foo/bam', self.args))

    def test_both(self):
        self.args.exclude = ['foo/bar']
        self.args.include = ['foo/bar']      
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.args))

    def test_include_multiple(self):
        self.args.include = ['foo/bar', 'foo/baz']
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.args))
        self.assertTrue(aomi.validation.specific_path_check('foo/baz', self.args))

    def test_exclude_multiple(self):
        self.args.exclude = ['foo/bar', 'foo/baz']
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.args))
        self.assertFalse(aomi.validation.specific_path_check('foo/baz', self.args))

    def test_both(self):
        self.args.exclude = ['foo/bar', 'foo/baz']
        self.args.include = ['foo/bar', 'foo/baz']        
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.args))
        self.assertFalse(aomi.validation.specific_path_check('foo/baz', self.args))
        self.assertFalse(aomi.validation.specific_path_check('foo/bam', self.args))

    def test_complex(self):
        self.args.include = ['foo/bar', 'foo/bam']
        self.args.exclude = ['foo/baz', 'foo/bam']
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.args))
        self.assertFalse(aomi.validation.specific_path_check('foo/bom', self.args))
        self.assertFalse(aomi.validation.specific_path_check('foo/bam', self.args))
        self.assertFalse(aomi.validation.specific_path_check('foo/baz', self.args))

class SanitizeMount(unittest.TestCase):
    def test_happy_path(self):
        assert aomi.validation.sanitize_mount('foo') == 'foo'
        assert aomi.validation.sanitize_mount('foo/bar') == 'foo/bar'

    def test_prefix(self):
        assert aomi.validation.sanitize_mount('/foo') == 'foo'
        assert aomi.validation.sanitize_mount('/foo/bar') == 'foo/bar'

    def test_suffix(self):
        assert aomi.validation.sanitize_mount('/foo') == 'foo'
        assert aomi.validation.sanitize_mount('/foo/bar') == 'foo/bar'

    def test_both(self):
        assert aomi.validation.sanitize_mount('/foo/') == 'foo'
        assert aomi.validation.sanitize_mount('/foo/bar/') == 'foo/bar'
        
