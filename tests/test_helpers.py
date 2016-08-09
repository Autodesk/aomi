import unittest
import aomi.helpers

class IsTaggedTest(unittest.TestCase):
    def test_happy_path(self):
        self.assertTrue(aomi.helpers.is_tagged([], []))

    def test_exclusion(self):
        self.assertFalse(aomi.helpers.is_tagged([], ['foo']))
        self.assertFalse(aomi.helpers.is_tagged(['foo'], ['bar']))
        self.assertFalse(aomi.helpers.is_tagged(['foo'], ['foo', 'bar']))

    def test_inclusion(self):
        self.assertTrue(aomi.helpers.is_tagged(['foo'], ['foo']))
        self.assertTrue(aomi.helpers.is_tagged(['foo', 'bar'], ['foo']))

