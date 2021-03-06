from datetime import datetime

from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    ItemNotFoundException,
    NotEnoughCoinsException,
    WalletNotFoundException,
    PermissionDeniedException,
)

from database import execute
from testcase import TestCase
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, uuid


def create_wallet(amount=200000, n=1, owner=None):
    if owner is None:
        owner = [super_uuid]
    clear_wallets()
    wallet_uuids = []
    wallet_keys = []
    for i in range(n):
        wallet_uuid = uuid()
        wallet_key = "1234512345"
        execute(
            "INSERT INTO currency_wallet (time_stamp, source_uuid, `key`, amount, user_uuid)"
            "VALUES (%s, %s, %s, %s, %s)",
            datetime.utcnow(),
            wallet_uuid,
            wallet_key,
            amount,
            owner[i],
        )
        wallet_uuids.append(wallet_uuid)
        wallet_keys.append(wallet_key)
    return (wallet_uuids[0], wallet_keys[0]) if n == 1 else (wallet_uuids, wallet_keys)


def clear_wallets():
    execute("TRUNCATE currency_wallet")


testing_product = "CPU Cooler Plus"


class TestShop(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestShop"):
        cls.client.close()

    def assert_valid_categories(self, categories, ids):
        indices = set(range(len(categories)))
        for name, category in categories.items():
            self.assertRegex(name, r"^[a-zA-Z0-9. -]{3,}$")
            self.assertIsInstance(category, dict)
            self.assertEqual(["categories", "index", "items"], sorted(category))
            self.assertIn(category["index"], indices)
            indices.remove(category["index"])

            items = category["items"]
            self.assertIsInstance(items, dict)
            for iname, item in items.items():
                self.assertRegex(iname, r"^[a-zA-Z0-9. -]{3,}$")
                self.assertIsInstance(item, dict)
                self.assertEqual(["id", "price", "related_ms"], sorted(item))
                self.assertNotIn(item["id"], ids)
                ids.add(item["id"])
                self.assertGreater(item["price"], 0)
                self.assertEqual("device", item["related_ms"])

            self.assert_valid_categories(category["categories"], ids)
        self.assertFalse(indices)

    def test_list_successful(self):
        result = self.client.ms("inventory", ["shop", "list"])
        self.assert_dict_with_keys(result, ["categories"])
        self.assert_valid_categories(result["categories"], set())

    def test_info_not_found(self):
        with self.assertRaises(ItemNotFoundException):
            self.client.ms("inventory", ["shop", "info"], product="Not Existing")

    def test_info_successful(self):
        expected = {
            "related_ms": "device",
            "price": 75000,
            "name": testing_product,
            "id": 301,
            "category": ["Cooler", None],
        }
        actual = self.client.ms("inventory", ["shop", "info"], product=testing_product)
        self.assertEqual(expected, actual)

    def test_buy_not_enough_coins(self):
        wallet_uuid, key = create_wallet(1)
        with self.assertRaises(NotEnoughCoinsException):
            self.client.ms(
                "inventory", ["shop", "buy"], products={testing_product: 1}, wallet_uuid=wallet_uuid, key=key
            )

    def test_buy_item_not_found(self):
        wallet_uuid, key = create_wallet()
        with self.assertRaises(ItemNotFoundException):
            self.client.ms(
                "inventory", ["shop", "buy"], products={"Does not exist": 1}, wallet_uuid=wallet_uuid, key=key
            )

    def test_buy_wallet_not_found(self):
        wallet_uuid, key = create_wallet()
        wallet_uuid = uuid()
        with self.assertRaises(WalletNotFoundException):
            self.client.ms(
                "inventory", ["shop", "buy"], products={testing_product: 1}, wallet_uuid=wallet_uuid, key=key
            )

    def test_buy_permission_denied(self):
        wallet_uuid, key = create_wallet()
        key = "5432154321"
        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "inventory", ["shop", "buy"], products={testing_product: 1}, wallet_uuid=wallet_uuid, key=key
            )

    def test_buy_successful(self):
        wallet_uuid, key = create_wallet()
        response = self.client.ms(
            "inventory", ["shop", "buy"], products={testing_product: 1}, wallet_uuid=wallet_uuid, key=key
        )
        self.assert_dict_with_keys(response, ["bought_products"])
        bought_products = response["bought_products"]
        self.assertIsInstance(bought_products, list)
        self.assertEqual(1, len(bought_products))
        product = bought_products[0]
        self.assert_dict_with_keys(product, ["element_name", "element_uuid", "owner", "related_ms"])
        self.assertEqual(testing_product, product["element_name"])
        self.assert_valid_uuid(product["element_uuid"])
        self.assertEqual(super_uuid, product["owner"])
        self.assertEqual("device", product["related_ms"])
