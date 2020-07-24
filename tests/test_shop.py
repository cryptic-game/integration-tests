from datetime import datetime
from unittest import TestCase

from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    ItemNotFoundException,
    NotEnoughCoinsException,
    WalletNotFoundException,
    PermissionDeniedException,
)

from database import execute
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, uuid


def create_wallet(amount=200000, owner=super_uuid):
    clear_wallets()
    wallet_uuid = uuid()
    wallet_key = "1234512345"
    execute(
        "INSERT INTO currency_wallet (time_stamp, source_uuid, `key`, amount, user_uuid) VALUES (%s, %s, %s, %s, %s)",
        datetime.now(),
        wallet_uuid,
        wallet_key,
        amount,
        owner,
    )
    return wallet_uuid, wallet_key


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

    def test_list_successful(self):
        actual = self.client.ms("inventory", ["shop", "list"])
        self.assertIsNotNone(actual["categories"]["Cooler"]["items"][testing_product])

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
        self.assertEqual(response["bought_products"][0]["element_name"], testing_product)
