from datetime import datetime
from unittest import TestCase

from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    UnknownSourceOrDestinationException,
    AlreadyOwnAWalletException,
    PermissionDeniedException,
    NotEnoughCoinsException
)

from database import execute
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, uuid
from tests.test_shop import clear_wallets, create_wallet


def create_transactions(wallet_uuid, n=1, amount=20):
    clear_transactions()
    for i in range(n):
        if i % 2 == 0:
            source_uuid = wallet_uuid
            destination_uuid = uuid()
        else:
            source_uuid = uuid()
            destination_uuid = wallet_uuid

        execute(
            "INSERT INTO currency_transaction(id, time_stamp, source_uuid,send_amount,destination_uuid,`usage`,origin)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s)",
            i + 1,
            datetime.now(),
            source_uuid,
            amount,
            destination_uuid,
            "test transaction " + str(i),
            0)


def clear_transactions():
    execute("TRUNCATE currency_transaction")


class TestCurrency(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestCurrency"):
        cls.client.close()

    def test_create_wallet_successful(self):
        clear_wallets()
        expected_keys = ["time_stamp", "source_uuid", "key", "amount", "user_uuid"]
        actual = self.client.ms("currency", ["create"])
        self.assertIsInstance(actual, dict)
        for key in expected_keys:
            self.assertIn(key, actual)

    def test_create_wallet_already_own(self):
        create_wallet()
        with self.assertRaises(AlreadyOwnAWalletException):
            self.client.ms("currency", ["create"])

    def test_get_wallet_successful(self):
        wallet_uuid, wallet_key = create_wallet()
        expected_keys = ["time_stamp", "source_uuid", "key", "amount", "user_uuid", "transactions"]
        actual = self.client.ms("currency", ["get"], source_uuid=wallet_uuid, key=wallet_key)
        self.assertIsInstance(actual, dict)
        for key in expected_keys:
            self.assertIn(key, actual)
        self.assertEqual(actual["source_uuid"], wallet_uuid)
        self.assertEqual(actual["key"], wallet_key)

    def test_get_wallet_unknown(self):
        wallet_uuid, wallet_key = create_wallet()
        wallet_uuid = uuid()
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms("currency", ["get"], source_uuid=wallet_uuid, key=wallet_key)

    def test_get_wallet_permission_denied(self):
        wallet_uuid, wallet_key = create_wallet()
        wallet_key = "5432154321"
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("currency", ["get"], source_uuid=wallet_uuid, key=wallet_key)

    def test_send_successful(self):
        wallet_uuids, wallet_keys = create_wallet(10, 2, [super_uuid, uuid()])
        expected = {"ok": True}
        actual = self.client.ms(
            "currency", ["send"], source_uuid=wallet_uuids[0], key=wallet_keys[0], send_amount=10,
            destination_uuid=wallet_uuids[1], usage="test"
        )

        self.assertEqual(actual, expected)

    def test_send_unknown(self):
        wallet_uuids, wallet_keys = create_wallet(10, 2, [super_uuid, uuid()])

        # unknown source uuid
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms(
                "currency", ["send"], source_uuid=uuid(), key=wallet_keys[0], send_amount=10,
                destination_uuid=wallet_uuids[1], usage="test"
            )
        # unknown destination_uuid
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms(
                "currency", ["send"], source_uuid=wallet_uuids[0], key=wallet_keys[0], send_amount=10,
                destination_uuid=uuid(), usage="test"
            )

    def test_send_permission_denied(self):
        wallet_uuids, wallet_keys = create_wallet(10, 2, [super_uuid, uuid()])
        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "currency", ["send"], source_uuid=wallet_uuids[0], key="5432154321", send_amount=10,
                destination_uuid=wallet_uuids[1], usage="test"
            )

    def test_send_not_enough_coins(self):
        wallet_uuids, wallet_keys = create_wallet(10, 2, [super_uuid, uuid()])
        with self.assertRaises(NotEnoughCoinsException):
            self.client.ms(
                "currency", ["send"], source_uuid=wallet_uuids[0], key=wallet_keys[0], send_amount=100,
                destination_uuid=wallet_uuids[1], usage="test"
            )

    def test_transactions_successful(self):
        wallet_uuid, wallet_key = create_wallet(230)
        create_transactions(wallet_uuid, 10, 23)
        expected_keys = ["id", "time_stamp", "source_uuid", "send_amount", "destination_uuid", "usage", "origin"]
        actual = self.client.ms(
            "currency", ["transactions"], source_uuid=wallet_uuid, key=wallet_key, count=20, offset=0
        )

        self.assertIsInstance(actual, dict)
        self.assertIn("transactions", actual)
        transactions = actual["transactions"]
        for _ in transactions:
            for key in expected_keys:
                self.assertIn(key, actual["transactions"][0])

    def test_transactions_unknown(self):
        wallet_uuid, wallet_key = create_wallet(230)
        create_transactions(wallet_uuid, 10, 23)
        wallet_uuid = uuid()
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms(
                "currency", ["transactions"], source_uuid=wallet_uuid, key=wallet_key, count=20, offset=0
            )

    def test_transactions_permission_denied(self):
        wallet_uuid, wallet_key = create_wallet(230)
        create_transactions(wallet_uuid, 10, 23)
        wallet_key = "5432154321"
        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "currency", ["transactions"], source_uuid=wallet_uuid, key=wallet_key, count=20, offset=0
            )

    def test_list_successful(self):
        wallet_uuid, _ = create_wallet(10)
        actual = self.client.ms("currency", ["list"])
        self.assertIsInstance(actual, dict)
        self.assertIn("wallets", actual)
        wallets = actual["wallets"]
        for wallet in wallets:
            self.assertEqual(wallet, wallet_uuid)

    def test_reset_successful(self):
        wallet_uuid, _ = create_wallet()
        expected = {"ok": True}
        actual = self.client.ms("currency", ["reset"], source_uuid=wallet_uuid)
        self.assertEqual(actual, expected)

    def test_reset_unknown(self):
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms("currency", ["reset"], source_uuid=uuid())

    def test_reset_permission_denied(self):
        wallet_uuid, _ = create_wallet(1, 1, [uuid()])
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("currency", ["reset"], source_uuid=wallet_uuid)

    def test_delete_successful(self):
        wallet_uuid, wallet_key = create_wallet()
        expected = {"ok": True}
        actual = self.client.ms("currency", ["delete"], source_uuid=wallet_uuid, key=wallet_key)
        self.assertEqual(actual, expected)

    def test_delete_unknown(self):
        _, wallet_key = create_wallet()
        wallet_uuid = uuid()
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms("currency", ["delete"], source_uuid=wallet_uuid, key=wallet_key)

    def test_delete_permission_denied(self):
        wallet_uuid, _ = create_wallet()
        wallet_key = "5432154321"
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("currency", ["delete"], source_uuid=wallet_uuid, key=wallet_key)
