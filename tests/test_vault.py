import unittest
from aomi.vault import grok_seconds, is_aws

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

