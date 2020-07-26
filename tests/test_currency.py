from datetime import datetime, timedelta

from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    UnknownSourceOrDestinationException,
    AlreadyOwnAWalletException,
    PermissionDeniedException,
    NotEnoughCoinsException,
)
from PyCrypCli.game_objects import Wallet

from database import execute
from testcase import TestCase
from tests.test_server import setup_account, super_password, super_uuid
from tests.test_shop import clear_wallets, create_wallet
from util import get_client, uuid


def create_transactions(wallet_uuid, n=1, amount=20):
    clear_transactions()
    now = datetime.utcnow()
    for i in range(n):
        if i % 2 == 0:
            source_uuid = wallet_uuid
            destination_uuid = uuid()
        else:
            source_uuid = uuid()
            destination_uuid = wallet_uuid

        execute(
            "INSERT INTO currency_transaction "
            "(id, time_stamp, source_uuid, send_amount, destination_uuid, `usage`, origin) "
            "VALUES (%s, %s, %s, %s, %s, %s, 0)",
            i + 1,
            now + timedelta(minutes=i),
            source_uuid,
            amount,
            destination_uuid,
            f"test transaction #{i + 1}",
        )


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
        result = self.client.ms("currency", ["create"])
        self.assert_dict_with_keys(result, ["amount", "key", "source_uuid", "time_stamp", "user_uuid"])
        self.assertEqual(0, result["amount"])
        self.assertRegex(result["key"], r"^[0-9a-f]{10}$")
        self.assert_valid_uuid(result["source_uuid"])
        self.assertLess(abs((datetime.utcnow() - datetime.fromisoformat(result["time_stamp"])).total_seconds()), 5)
        self.assertEqual(super_uuid, result["user_uuid"])

    def test_create_wallet_already_own(self):
        create_wallet()
        with self.assertRaises(AlreadyOwnAWalletException):
            self.client.ms("currency", ["create"])

    def test_get_wallet_successful(self):
        wallet_uuid, wallet_key = create_wallet(amount=1337)
        create_transactions(wallet_uuid, n=3)

        result = self.client.ms("currency", ["get"], source_uuid=wallet_uuid, key=wallet_key)
        self.assert_dict_with_keys(result, ["amount", "key", "source_uuid", "time_stamp", "transactions", "user_uuid"])
        self.assertEqual(1337, result["amount"])
        self.assertEqual(wallet_key, result["key"])
        self.assertEqual(wallet_uuid, result["source_uuid"])
        self.assertLess(abs((datetime.utcnow() - datetime.fromisoformat(result["time_stamp"])).total_seconds()), 5)
        self.assertEqual(3, result["transactions"])
        self.assertEqual(super_uuid, result["user_uuid"])

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
        wallet_uuids, wallet_keys = create_wallet(amount=10, n=2, owner=[super_uuid, uuid()])
        expected = {"ok": True}
        actual = self.client.ms(
            "currency",
            ["send"],
            source_uuid=wallet_uuids[0],
            key=wallet_keys[0],
            send_amount=10,
            destination_uuid=wallet_uuids[1],
            usage="test",
        )

        self.assertEqual(actual, expected)

        self.assertEqual(0, Wallet.get_wallet(self.client, wallet_uuids[0], wallet_keys[0]).amount)
        self.assertEqual(20, Wallet.get_wallet(self.client, wallet_uuids[1], wallet_keys[1]).amount)

    def test_send_unknown(self):
        wallet_uuids, wallet_keys = create_wallet(10, 2, [super_uuid, uuid()])

        # unknown source uuid
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms(
                "currency",
                ["send"],
                source_uuid=uuid(),
                key=wallet_keys[0],
                send_amount=10,
                destination_uuid=wallet_uuids[1],
                usage="test",
            )

        # unknown destination_uuid
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms(
                "currency",
                ["send"],
                source_uuid=wallet_uuids[0],
                key=wallet_keys[0],
                send_amount=10,
                destination_uuid=uuid(),
                usage="test",
            )

    def test_send_permission_denied(self):
        wallet_uuids, wallet_keys = create_wallet(10, 2, [super_uuid, uuid()])
        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "currency",
                ["send"],
                source_uuid=wallet_uuids[0],
                key="5432154321",
                send_amount=10,
                destination_uuid=wallet_uuids[1],
                usage="test",
            )

    def test_send_not_enough_coins(self):
        wallet_uuids, wallet_keys = create_wallet(10, 2, [super_uuid, uuid()])
        with self.assertRaises(NotEnoughCoinsException):
            self.client.ms(
                "currency",
                ["send"],
                source_uuid=wallet_uuids[0],
                key=wallet_keys[0],
                send_amount=100,
                destination_uuid=wallet_uuids[1],
                usage="test",
            )

    def test_transactions_successful(self):
        wallet_uuid, wallet_key = create_wallet(amount=230)
        now = datetime.utcnow()
        create_transactions(wallet_uuid, n=10, amount=23)
        result = self.client.ms(
            "currency", ["transactions"], source_uuid=wallet_uuid, key=wallet_key, count=20, offset=0
        )

        self.assert_dict_with_keys(result, ["transactions"])
        transactions = result["transactions"]
        self.assertEqual(10, len(transactions))
        for i, transaction in enumerate(reversed(transactions)):
            self.assert_dict_with_keys(
                transaction, ["destination_uuid", "id", "origin", "send_amount", "source_uuid", "time_stamp", "usage"],
            )
            self.assertIn(wallet_uuid, [transaction["source_uuid"], transaction["destination_uuid"]])
            self.assertGreaterEqual(transaction["id"], 0)
            self.assertEqual(0, transaction["origin"])
            self.assertEqual(23, transaction["send_amount"])
            self.assertEqual(f"test transaction #{i + 1}", transaction["usage"])

            expected_timestamp = now + timedelta(minutes=i)
            actual_timestamp = datetime.fromisoformat(transaction["time_stamp"])
            self.assertLess(abs((expected_timestamp - actual_timestamp).total_seconds()), 10)

    def test_transactions_unknown(self):
        wallet_uuid, wallet_key = create_wallet(230)
        create_transactions(wallet_uuid, 10, 23)
        wallet_uuid = uuid()
        with self.assertRaises(UnknownSourceOrDestinationException):
            self.client.ms("currency", ["transactions"], source_uuid=wallet_uuid, key=wallet_key, count=20, offset=0)

    def test_transactions_permission_denied(self):
        wallet_uuid, wallet_key = create_wallet(230)
        create_transactions(wallet_uuid, 10, 23)
        wallet_key = "5432154321"
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("currency", ["transactions"], source_uuid=wallet_uuid, key=wallet_key, count=20, offset=0)

    def test_list_successful(self):
        wallet_uuid, _ = create_wallet(10)
        expected = {"wallets": [wallet_uuid]}
        actual = self.client.ms("currency", ["list"])
        self.assertEqual(expected, actual)

    def test_reset_successful(self):
        wallet_uuid, key = create_wallet()
        expected = {"ok": True}
        actual = self.client.ms("currency", ["reset"], source_uuid=wallet_uuid)
        self.assertEqual(actual, expected)

        with self.assertRaises(UnknownSourceOrDestinationException):
            Wallet.get_wallet(self.client, wallet_uuid, key)

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

        with self.assertRaises(UnknownSourceOrDestinationException):
            Wallet.get_wallet(self.client, wallet_uuid, wallet_key)

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
