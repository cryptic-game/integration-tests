from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    CannotTradeWithYourselfException,
    ItemNotFoundException,
    UserUUIDDoesNotExistException
)

from database import execute
from testcase import TestCase
from tests.test_device import add_inventory_element, clear_inventory
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, uuid


def create_random_user():
    execute(
        "INSERT INTO user (uuid, created,last, name, password) VALUES"
        " (%s, current_timestamp, current_timestamp, 'test', %s)",
        user := uuid(),
        uuid(),
    )
    return user


class TestInventory(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestInventory"):
        cls.client.close()

    def test_inventory_list_successful(self):
        clear_inventory()
        element_uuid = add_inventory_element("CPU Cooler Plus")
        actual = self.client.ms("inventory", ["inventory", "list"])
        self.assert_dict_with_keys(actual, ["elements"])
        for element in actual["elements"]:
            self.assertEqual(super_uuid, element["owner"])
            self.assertEqual("", element["related_ms"])
            self.assertEqual(element_uuid, element["element_uuid"])
            self.assertEqual("CPU Cooler Plus", element["element_name"])

    def test_inventory_trade_successful(self):
        clear_inventory()
        element_uuid = add_inventory_element("CPU Cooler Plus")
        trade_user = create_random_user()
        expected = {"ok": True}
        actual = self.client.ms("inventory", ["inventory", "trade"], element_uuid=element_uuid, target=trade_user)
        self.assertEqual(actual, expected)

    def test_inventory_trade_item_not_found(self):
        with self.assertRaises(ItemNotFoundException):
            self.client.ms("inventory", ["inventory", "trade"], element_uuid=uuid(), target=uuid())

    def test_inventory_trade_cannot_trade_with_yourself(self):
        clear_inventory()
        element_uuid = add_inventory_element("CPU Cooler Plus")
        with self.assertRaises(CannotTradeWithYourselfException):
            self.client.ms("inventory", ["inventory", "trade"], element_uuid=element_uuid, target=super_uuid)

    def test_inventory_trade_user_does_not_exists(self):
        clear_inventory()
        element_uuid = add_inventory_element("CPU Cooler Plus")
        with self.assertRaises(UserUUIDDoesNotExistException):
            self.client.ms("inventory", ["inventory", "trade"], element_uuid=element_uuid, target=uuid())
