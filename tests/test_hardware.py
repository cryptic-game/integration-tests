from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    ElementPartNotFoundException,
    MissingPartException,
    DeviceNotFoundException,
)

from database import execute
from testcase import TestCase
from tests.test_device import clear_devices, clear_inventory, add_inventory_element
from tests.test_server import setup_account, super_password
from util import get_client, uuid


class TestHardware(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestHardware"):
        cls.client.close()

    def get_starter_configuration(self) -> dict:
        return self.client.get_hardware_config()["start_pc"]

    def test_build_part_not_found(self):
        clear_devices()

        config = self.get_starter_configuration()
        for part in ["mainboard", "powerPack", "case"]:
            with self.assertRaises(ElementPartNotFoundException) as ctx:
                self.client.ms("device", ["hardware", "build"], **{**config, part: "notfound42"})
            exception: ElementPartNotFoundException = ctx.exception
            self.assertEqual([part], exception.params)
        for part in ["cpu", "processorCooler", "gpu", "ram", "disk"]:
            with self.assertRaises(ElementPartNotFoundException) as ctx:
                self.client.ms("device", ["hardware", "build"], **{**config, part: ["notfound42"]})
            exception: ElementPartNotFoundException = ctx.exception
            self.assertEqual([part], exception.params)

    def test_build_part_not_chosen(self):
        clear_devices()
        clear_inventory()

        config = self.get_starter_configuration()
        for part, name in config.items():
            if name:
                add_inventory_element(name[0] if isinstance(name, list) else name)

        for part in ["cpu", "ram", "disk"]:
            with self.assertRaises(MissingPartException) as ctx:
                self.client.ms("device", ["hardware", "build"], **{**config, part: []})
            exception: MissingPartException = ctx.exception
            self.assertEqual([part], exception.params)

    def test_build_successful(self):
        clear_devices()
        clear_inventory()

        config = self.get_starter_configuration()
        for _, name in config.items():
            if name:
                add_inventory_element(name[0] if isinstance(name, list) else name)

        result = self.client.ms("device", ["hardware", "build"], **config)
        self.assert_dict_with_keys(result, ["success", "performance"])
        self.assertTrue(result["success"])
        performance = result["performance"]
        self.assertIsInstance(performance, list)
        self.assertEqual(5, len(performance))
        for e in performance:
            self.assertIsInstance(e, (int, float))

    def test_resources_successful(self):
        clear_devices()
        execute("TRUNCATE device_workload")
        execute(
            "INSERT INTO device_workload "
            "(uuid, performance_cpu, performance_gpu, performance_ram, performance_disk, performance_network, "
            "usage_cpu, usage_gpu, usage_ram, usage_disk, usage_network) VALUES "
            "(%s, 10, 20, 40, 80, 160, 1, 4, 16, 64, 256)",
            device_uuid := uuid(),
        )

        expected = {
            "cpu": 0.1,
            "gpu": 0.2,
            "ram": 0.4,
            "disk": 0.8,
            "network": 1,
        }
        actual = self.client.ms("device", ["hardware", "resources"], device_uuid=device_uuid)

        self.assertEqual(expected, actual)

    def test_resources_device_not_found(self):
        clear_devices()

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["hardware", "resources"], device_uuid=uuid())
