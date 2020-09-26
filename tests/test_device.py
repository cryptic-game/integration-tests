from typing import List

from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    AlreadyOwnADeviceException,
    DeviceNotFoundException,
    PermissionDeniedException,
    DevicePoweredOffException,
    MaximumDevicesReachedException,
    ElementPartNotFoundException,
    PartNotInInventoryException,
    MissingPartException,
    MicroserviceException,
)
from PyCrypCli.game_objects import Device

from database import execute
from testcase import TestCase
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, uuid


def clear_devices():
    execute("TRUNCATE device_device")


def clear_inventory():
    execute("TRUNCATE inventory_inventory")


def setup_device(n=1, owner=super_uuid, starter_device=False) -> List[str]:
    clear_devices()
    out = []
    for i in range(n):
        out.append(uuid())
        execute(
            "INSERT INTO device_device (uuid, name, owner, powered_on, starter_device) VALUES (%s, %s, %s, %s, %s)",
            out[-1],
            f"test{i + 1}",
            owner,
            i % 2 == 0,
            starter_device and i == 0,
        )
    return out


def add_inventory_element(name):
    element_uuid = uuid()
    execute(
        "INSERT INTO inventory_inventory (element_uuid, element_name, related_ms, owner) VALUES (%s, %s, '', %s)",
        element_uuid,
        name,
        super_uuid,
    )
    return element_uuid


class DeviceIsStarterDeviceException(MicroserviceException):
    error: str = "device_is_starter_device"


class TestDevice(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestDevice"):
        cls.client.close()

    def get_starter_configuration(self) -> dict:
        return self.client.get_hardware_config()["start_pc"]

    def assert_valid_device(self, data: dict, starter_device: bool):
        self.assert_dict_with_keys(data, ["name", "owner", "powered_on", "uuid", "starter_device"])
        self.assertRegex(data["name"], r"^[a-zA-Z0-9\-_]{1,15}$")
        self.assertEqual(super_uuid, data["owner"])
        self.assertEqual(True, data["powered_on"])
        self.assert_valid_uuid(data["uuid"])
        self.assertEqual(starter_device, data["starter_device"])

    def test_starter_device_failed(self):
        setup_device()

        with self.assertRaises(AlreadyOwnADeviceException):
            self.client.ms("device", ["device", "starter_device"])

    def test_starter_device_successful(self):
        clear_devices()

        self.assert_valid_device(self.client.ms("device", ["device", "starter_device"]), True)

    def test_ping_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["device", "ping"], device_uuid=uuid())

    def test_ping_successful(self):
        device_uuid = setup_device()[0]

        self.assertEqual({"online": True}, self.client.ms("device", ["device", "ping"], device_uuid=device_uuid))
        execute("UPDATE device_device SET powered_on=false WHERE uuid=%s", device_uuid)
        self.assertEqual({"online": False}, self.client.ms("device", ["device", "ping"], device_uuid=device_uuid))

    def test_info_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["device", "info"], device_uuid=uuid())

    def test_info_successful(self):
        clear_devices()
        device = Device.starter_device(self.client)

        result = self.client.ms("device", ["device", "info"], device_uuid=device.uuid)

        self.assert_dict_with_keys(result, ["hardware", "name", "owner", "powered_on", "uuid", "starter_device"])
        self.assertEqual(device.uuid, result["uuid"])
        self.assertEqual(True, result["powered_on"])
        self.assertEqual(super_uuid, result["owner"])
        self.assertEqual(device.name, result["name"])

        hardware: List[dict] = result["hardware"]
        self.assertIsInstance(hardware, list)
        self.assertEqual(7, len(hardware))
        types = {"mainboard", "cpu", "processorCooler", "ram", "disk", "powerPack", "case"}
        for element in hardware:
            self.assert_dict_with_keys(element, ["device_uuid", "hardware_element", "hardware_type", "uuid"])
            self.assertEqual(device.uuid, element["device_uuid"])
            self.assert_valid_uuid(element["uuid"])
            self.assertIn(element["hardware_type"], types)
            types.remove(element["hardware_type"])
            self.assertRegex(element["hardware_element"], r"^[a-zA-Z0-9 .-]+$")

    def test_all(self):
        devices = {x: i for i, x in enumerate(setup_device(3))}

        result = self.client.ms("device", ["device", "all"])
        self.assert_dict_with_keys(result, ["devices"])
        self.assertIsInstance(result["devices"], list)
        self.assertEqual(3, len(result["devices"]))
        for device in result["devices"]:
            self.assertIsInstance(device, dict)
            self.assert_dict_with_keys(device, ["name", "owner", "powered_on", "uuid", "starter_device"])
            device_uuid = device["uuid"]
            self.assert_valid_uuid(device_uuid)
            self.assertIn(device_uuid, devices)
            pos = devices[device_uuid]
            self.assertEqual(f"test{pos + 1}", device["name"])
            devices.pop(device_uuid)
            self.assertEqual(super_uuid, device["owner"])
            self.assertEqual(pos % 2 == 0, device["powered_on"])

    def test_power_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["device", "power"], device_uuid=uuid())

    def test_power_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("device", ["device", "power"], device_uuid=device_uuid)

    def test_power_successful(self):
        clear_devices()
        device = Device.starter_device(self.client)

        expected = {
            "uuid": device.uuid,
            "name": device.name,
            "owner": super_uuid,
            "powered_on": False,
            "starter_device": True,
        }
        actual = self.client.ms("device", ["device", "power"], device_uuid=device.uuid)
        self.assertEqual(expected, actual)

        device.update()
        self.assertEqual(False, device.powered_on)

        expected = {
            "uuid": device.uuid,
            "name": device.name,
            "owner": super_uuid,
            "powered_on": True,
            "starter_device": True,
        }
        actual = self.client.ms("device", ["device", "power"], device_uuid=device.uuid)
        self.assertEqual(expected, actual)

        device.update()
        self.assertEqual(True, device.powered_on)

    def test_change_name_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["device", "change_name"], device_uuid=uuid(), name="foobar")

    def test_change_name_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("device", ["device", "change_name"], device_uuid=device_uuid, name="foobar")

    def test_change_name_powered_off(self):
        device_uuid = setup_device(2)[1]

        with self.assertRaises(DevicePoweredOffException):
            self.client.ms("device", ["device", "change_name"], device_uuid=device_uuid, name="foobar")

    def test_change_name_successful(self):
        device_uuid = setup_device()[0]

        expected = {
            "uuid": device_uuid,
            "name": "foobar",
            "owner": super_uuid,
            "powered_on": True,
            "starter_device": False,
        }
        actual = self.client.ms("device", ["device", "change_name"], device_uuid=device_uuid, name="foobar")
        self.assertEqual(expected, actual)

        device = Device.get_device(self.client, device_uuid)
        self.assertEqual("foobar", device.name)

    def test_delete_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["device", "delete"], device_uuid=uuid())

    def test_delete_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("device", ["device", "delete"], device_uuid=device_uuid)

    def test_delete_starter_device(self):
        clear_devices()
        device = Device.starter_device(self.client)

        with self.assertRaises(DeviceIsStarterDeviceException):
            self.client.ms("device", ["device", "delete"], device_uuid=device.uuid)

    def test_delete_successful(self):
        clear_devices()
        device = Device.starter_device(self.client)
        execute("UPDATE device_device SET starter_device=FALSE WHERE uuid=%s", device.uuid)

        expected = {"ok": True}
        actual = self.client.ms("device", ["device", "delete"], device_uuid=device.uuid)
        self.assertEqual(expected, actual)

        with self.assertRaises(DeviceNotFoundException):
            device.update()

    def test_spot_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["device", "spot"])

    def test_spot_successful(self):
        owner = uuid()
        device_uuids = setup_device(n=5, owner=owner)
        devices = []
        for i, x in enumerate(device_uuids):
            if i % 2 == 0:
                devices.append(
                    {"uuid": x, "name": f"test{i + 1}", "owner": owner, "powered_on": True, "starter_device": False}
                )

        for _ in range(10):
            self.assertIn(self.client.ms("device", ["device", "spot"]), devices)

    def test_create_max_devices_reached(self):
        setup_device(3)

        with self.assertRaises(MaximumDevicesReachedException):
            self.client.ms(
                "device",
                ["device", "create"],
                gpu=[],
                cpu=[],
                mainboard="x",
                ram=[],
                disk=[],
                processorCooler=[],
                powerPack="x",
                case="x",
            )

    def test_create_part_not_found(self):
        clear_devices()

        config = self.get_starter_configuration()
        for part in ["mainboard", "powerPack", "case"]:
            with self.assertRaises(ElementPartNotFoundException) as ctx:
                self.client.ms("device", ["device", "create"], **{**config, part: "doesntexist123"})
            exception: ElementPartNotFoundException = ctx.exception
            self.assertEqual((part,), exception.params)
        for part in ["cpu", "processorCooler", "gpu", "ram", "disk"]:
            with self.assertRaises(ElementPartNotFoundException) as ctx:
                self.client.ms("device", ["device", "create"], **{**config, part: ["doesntexist123"]})
            exception: ElementPartNotFoundException = ctx.exception
            self.assertEqual((part,), exception.params)

    def test_create_part_not_in_inventory(self):
        clear_devices()
        clear_inventory()

        config = self.get_starter_configuration()
        for part, name in config.items():
            if name:
                add_inventory_element(name[0] if isinstance(name, list) else name)

        for part, name in config.items():
            if not name:
                continue
            name: str = name[0] if isinstance(name, list) else name
            execute("DELETE FROM inventory_inventory WHERE element_name=%s", name)
            with self.assertRaises(PartNotInInventoryException) as ctx:
                self.client.ms("device", ["device", "create"], **config)
            exception: PartNotInInventoryException = ctx.exception
            self.assertEqual((part,), exception.params)
            add_inventory_element(name)

    def test_create_part_not_chosen(self):
        clear_devices()
        clear_inventory()

        config = self.get_starter_configuration()
        for part, name in config.items():
            if name:
                add_inventory_element(name[0] if isinstance(name, list) else name)

        for part in ["cpu", "ram", "disk"]:
            with self.assertRaises(MissingPartException) as ctx:
                self.client.ms("device", ["device", "create"], **{**config, part: []})
            exception: MissingPartException = ctx.exception
            self.assertEqual((part,), exception.params)

    def test_create_successful(self):
        clear_devices()
        clear_inventory()

        config = self.get_starter_configuration()
        for _, name in config.items():
            if name:
                add_inventory_element(name[0] if isinstance(name, list) else name)

        self.assert_valid_device(self.client.ms("device", ["device", "create"], **config), False)
