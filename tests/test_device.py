from unittest import TestCase

from PyCrypCli.client import Client
from PyCrypCli.exceptions import AlreadyOwnADeviceException, DeviceNotFoundException

from database import execute
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, is_uuid, uuid

device_uuid = uuid()


def clear_devices():
    execute("TRUNCATE device_device")


def setup_device():
    clear_devices()
    execute(
        "INSERT INTO device_device (uuid, name, owner, powered_on) VALUES (%s, %s, %s, true)",
        device_uuid,
        "test",
        super_uuid,
    )


class TestDevice(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestDevice"):
        cls.client.close()

    def test_starter_device_failed(self):
        setup_device()

        with self.assertRaises(AlreadyOwnADeviceException):
            self.client.ms("device", ["device", "starter_device"])

    def test_starter_device_successful(self):
        clear_devices()

        result = self.client.ms("device", ["device", "starter_device"])
        self.assertIsInstance(result, dict)
        self.assertEqual(["name", "owner", "powered_on", "uuid"], sorted(result))
        self.assertRegex(result["name"], r"^[a-zA-Z0-9\-_]{1,15}$")
        self.assertEqual(super_uuid, result["owner"])
        self.assertEqual(True, result["powered_on"])
        self.assertTrue(is_uuid(result["uuid"]))

    def test_ping_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["device", "ping"], device_uuid=device_uuid)

    def test_ping_successful(self):
        setup_device()

        self.assertEqual({"online": True}, self.client.ms("device", ["device", "ping"], device_uuid=device_uuid))
        execute("UPDATE device_device SET powered_on=false WHERE uuid=%s", device_uuid)
        self.assertEqual({"online": False}, self.client.ms("device", ["device", "ping"], device_uuid=device_uuid))
