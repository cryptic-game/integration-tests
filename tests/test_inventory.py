from PyCrypCli.client import Client
from PyCrypCli.exceptions import CannotTradeWithYourselfException, ItemNotFoundException, UserUUIDDoesNotExistException
from PyCrypCli.game_objects import InventoryElement

from database import execute
from testcase import TestCase
from tests.test_device import add_inventory_element, clear_inventory
from tests.test_server import setup_account, super_password, super_uuid, super_hash
from util import get_client, uuid


def create_random_user() -> str:
    execute(
        "INSERT INTO user (uuid, created, last, name, password) VALUES "
        "(%s, current_timestamp, current_timestamp, 'test', %s)",
        user := uuid(),
        super_hash,
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

        expected = {
            "elements": [
                {
                    "element_uuid": element_uuid,
                    "element_name": "CPU Cooler Plus",
                    "related_ms": "",
                    "owner": super_uuid,
                }
            ]
        }
        actual = self.client.ms("inventory", ["inventory", "list"])

        self.assertEqual(expected, actual)

    def test_inventory_trade_successful(self):
        clear_inventory()
        element_uuid = add_inventory_element("CPU Cooler Plus")
        trade_user = create_random_user()

        expected = {"ok": True}
        actual = self.client.ms("inventory", ["inventory", "trade"], element_uuid=element_uuid, target=trade_user)

        self.assertEqual(actual, expected)

        client: Client = get_client()
        client.login("test", super_password)

        result = InventoryElement.list_inventory(client)
        self.assertEqual(1, len(result))
        self.assertEqual(trade_user, result[0].owner)
        self.assertEqual("", result[0].related_ms)
        self.assertEqual(element_uuid, result[0].uuid)
        self.assertEqual("CPU Cooler Plus", result[0].name)

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
