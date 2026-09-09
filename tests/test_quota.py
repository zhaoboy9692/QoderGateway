import unittest
from qoder2api.tokens import quota_is_exhausted

class QuotaTests(unittest.TestCase):
    def test_resource_package_keeps_account_usable(self):
        self.assertFalse(quota_is_exhausted({'isQuotaExceeded': False, 'userQuota': {'remaining': 0}, 'orgResourcePackage': {'available': True, 'remaining': 8970}}))
    def test_all_available_pools_exhausted(self):
        self.assertTrue(quota_is_exhausted({'userQuota': {'remaining': 0}, 'orgResourcePackage': {'available': True, 'remaining': 0}}))
    def test_explicit_upstream_exhaustion_is_authoritative(self):
        self.assertTrue(quota_is_exhausted({'isQuotaExceeded': True}))
    def test_unknown_is_not_exhausted(self):
        self.assertFalse(quota_is_exhausted({}))
        self.assertFalse(quota_is_exhausted({'userQuota': {'remaining': 0}, 'orgResourcePackage': {'available': True}}))
    def test_absent_or_unavailable_package_does_not_add_credits(self):
        self.assertTrue(quota_is_exhausted({'userQuota': {'remaining': 0}}))
        self.assertTrue(quota_is_exhausted({'userQuota': {'remaining': 0}, 'orgResourcePackage': {'available': False, 'remaining': 9000}}))
