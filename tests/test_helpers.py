import unittest
import aomi.helpers

class IsTaggedTest(unittest.TestCase):
    def test_happy_path(self):
        self.assertTrue(aomi.helpers.is_tagged([], []))

    def test_exclusion(self):
        self.assertFalse(aomi.helpers.is_tagged([], ['foo']))
        self.assertFalse(aomi.helpers.is_tagged(['foo'], ['bar']))
        self.assertFalse(aomi.helpers.is_tagged(['foo', 'bar'], ['foo']))

    def test_inclusion(self):
        self.assertTrue(aomi.helpers.is_tagged(['foo'], ['foo']))
        self.assertTrue(aomi.helpers.is_tagged(['foo'], ['foo', 'bar']))

class CliHashTest(unittest.TestCase):
    def test_happy_path(self):
        assert aomi.helpers.cli_hash(["foo=bar"]) == {'foo': 'bar'}
        assert aomi.helpers.cli_hash(["foo=bar", "baz=bam"]) == {'foo': 'bar', 'baz': 'bam'}


class FilePathTest(unittest.TestCase):
    def test_subdir_happy_path(self):
        assert aomi.helpers.subdir_path("/a/b/c", "/a/b/.gitignore") == "c"
        assert aomi.helpers.subdir_path("/a/b/c/d", "/a/b/.gitignore") == "c/d"

    def test_subdir_missing(self):
        assert aomi.helpers.subdir_path("/a/b/c", "c/d") is None

    def test_subdir_external(self):
        assert aomi.helpers.subdir_path("/a/b/c", "/d/e") is None
