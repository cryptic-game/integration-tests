import unittest
from typing import List


class TestCase(unittest.TestCase):
    def assert_valid_uuid(self, text: str):
        self.assertIsInstance(text, str)
        self.assertRegex(text, r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")

    def assert_dict_with_keys(self, obj: dict, keys: List[str]):
        self.assertIsInstance(obj, dict)
        self.assertEqual(sorted(keys), sorted(obj))
