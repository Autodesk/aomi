import unittest
from aomi.seed import sanitize_mount

class SanitizeMount(unittest.TestCase):
    def test_happy_path(self):
        assert sanitize_mount('foo') == 'foo'
        assert sanitize_mount('foo/bar') == 'foo/bar'

    def test_prefix(self):
        assert sanitize_mount('/foo') == 'foo'
        assert sanitize_mount('/foo/bar') == 'foo/bar'

    def test_suffix(self):
        assert sanitize_mount('/foo') == 'foo'
        assert sanitize_mount('/foo/bar') == 'foo/bar'

    def test_both(self):
        assert sanitize_mount('/foo/') == 'foo'
        assert sanitize_mount('/foo/bar/') == 'foo/bar'
