import unittest
import aomi.exceptions
import aomi.validation
from aomi.cli import parser_factory
from cryptorito import portable_b64encode, portable_b64decode


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
        

class StringTests(unittest.TestCase):
    ghost_emoji = portable_b64decode('8J+Ruwo=')
    some_binary = portable_b64decode('uRo/OptvvkT790yaPjql5OItfFUBSM2tM42QJkPM7qvMTn4tQClPjB6mpdSFDtyzuqGVrMGaHRKv7XuzlZPpWGbVzlCjIvN0nOUiBXSQsockEJwCwIaiwm/xxWSE9+P2zWdqt1J/Iuwv6Rq60qpMRTqWNJD5dDzbw4VdDQhxzgK4zN2Er+JQQqQctsj1XuM8xJtzBQsozt5ZCJso4/jsUsWrFgHPp5nu4whuT7ZSgthsGz+NXo1f6v4njJ705ZMjLW0zdnkx/14E8qGJCsDs8pCkekDn+K4gTLfzZHga/du8xtN6e/X97K2BbdVC8Obz684wnqdHLWc+bNNso+5XFtQbFbK6vBtGtZNmBeiVBo594Zr5xRxFPSfOHIKz0jB4U5He7xgh2C7AFh2SCy4fW1fwC5XxQoz1pRSiFTRbUr/dMHMn0ZaspVYUNPdZccM4xj8ip5k4fXVRTKFF1qEiFGohcfLdabCBXAkckOmGogdN0swOpoiNEohYksW0bkof89q1aRJl6tM9E2spH62XZXDmQFHIdxFFHP6zAl2t7zGB2vxDCpLgQg3l8RytryMfDR7MXXXy2kbhtFpIl45gFl/8u+aOc7fP4dLxacCbJNz3cO3iMXIPytwiaq5HJbgQ6ZgeGjZBniTCRLwRpOv3l3GRsLstdRJSk2KP+kwY9Tk=')

    def test_is_unicode(self):
        assert aomi.validation.is_unicode_string("foo") == None
        assert aomi.validation.is_unicode_string("70758F21-946C-4C14-AD67-53DDCA5C9F4B") == None
        assert aomi.validation.is_unicode_string(self.ghost_emoji) == None
        with self.assertRaises(aomi.exceptions.Validation):
            aomi.validation.is_unicode_string(self.some_binary)


class UnicodeTests(unittest.TestCase):
    def test_is_unicode(self):
        assert aomi.validation.is_unicode(str("test a thing"))
