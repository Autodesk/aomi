import unittest
import aomi.validation
from aomi.cli import parser_factory

class FilePathTest(unittest.TestCase):
    def subdir_happy_path(self):
        assert aomi.validation.subdir_file("/a/b/c", "b/c") == "b/c"

    def subdir_missing(self):
        assert aomi.validation.subdir_file("/a/b/c", "c/d") == None

class VaultPathTest(unittest.TestCase):
    def setUp(self):
        parser = parser_factory('seed')
        self.opt = parser.parse_args()[0]

    def test_happy_path(self):
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.opt))
        self.assertTrue(aomi.validation.specific_path_check('foo/bam', self.opt))

    def test_include(self):
        self.opt.include = ['foo/bar']
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.opt))
        self.assertFalse(aomi.validation.specific_path_check('foo/bam', self.opt))

    def test_exclude(self):
        self.opt.exclude = ['foo/bar']
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.opt))
        self.assertTrue(aomi.validation.specific_path_check('foo/bam', self.opt))

    def test_both(self):
        self.opt.exclude = ['foo/bar']
        self.opt.include = ['foo/bar']      
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.opt))

    def test_include_multiple(self):
        self.opt.include = ['foo/bar', 'foo/baz']
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.opt))
        self.assertTrue(aomi.validation.specific_path_check('foo/baz', self.opt))

    def test_exclude_multiple(self):
        self.opt.exclude = ['foo/bar', 'foo/baz']
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.opt))
        self.assertFalse(aomi.validation.specific_path_check('foo/baz', self.opt))

    def test_both(self):
        self.opt.exclude = ['foo/bar', 'foo/baz']
        self.opt.include = ['foo/bar', 'foo/baz']        
        self.assertFalse(aomi.validation.specific_path_check('foo/bar', self.opt))
        self.assertFalse(aomi.validation.specific_path_check('foo/baz', self.opt))
        self.assertFalse(aomi.validation.specific_path_check('foo/bam', self.opt))

    def test_complex(self):
        self.opt.include = ['foo/bar', 'foo/bam']
        self.opt.exclude = ['foo/baz', 'foo/bam']
        self.assertTrue(aomi.validation.specific_path_check('foo/bar', self.opt))
        self.assertFalse(aomi.validation.specific_path_check('foo/bom', self.opt))
        self.assertFalse(aomi.validation.specific_path_check('foo/bam', self.opt))
        self.assertFalse(aomi.validation.specific_path_check('foo/baz', self.opt))

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
        
