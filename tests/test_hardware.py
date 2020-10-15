from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    ElementPartNotFoundException,
    MissingPartException,
    DeviceNotFoundException,
    ServiceNotFoundException,
)

from database import execute
from testcase import TestCase
from tests.test_device import clear_devices, clear_inventory, add_inventory_element
from tests.test_server import setup_account, super_password
from util import get_client, uuid

ELEMENT_TYPES = ["mainboard", "cpu", "ram", "gpu", "disk", "processorCooler", "powerPack", "case"]


def setup_workload() -> str:
    clear_devices()
    execute("TRUNCATE device_workload")
    execute(
        "INSERT INTO device_workload "
        "(uuid, performance_cpu, performance_gpu, performance_ram, performance_disk, performance_network, "
        "usage_cpu, usage_gpu, usage_ram, usage_disk, usage_network) VALUES "
        "(%s, 10, 20, 40, 80, 160, 1, 4, 16, 64, 256)",
        device_uuid := uuid(),
    )
    return device_uuid


def setup_service_req(device_uuid) -> str:
    execute("TRUNCATE device_service_req")
    execute(
        "INSERT INTO device_service_req "
        "(service_uuid, device_uuid, allocated_cpu, allocated_ram, allocated_gpu, allocated_disk, allocated_network) "
        "VALUES (%s, %s, 1, 4, 2, 8, 16)",
        service_uuid := uuid(),
        device_uuid,
    )
    return service_uuid


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
        device_uuid = setup_workload()

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

    def test_process_successful(self):
        device_uuid = setup_workload()
        service_uuid = setup_service_req(device_uuid)

        expected = {
            "cpu": 1.0,
            "ram": 2.0,
            "gpu": 4.0,
            "disk": 8.0,
            "network": 10.0,
        }
        actual = self.client.ms("device", ["hardware", "process"], service_uuid=service_uuid)

        self.assertEqual(expected, actual)

    def test_process_service_not_found(self):
        execute("TRUNCATE device_service_req")

        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("device", ["hardware", "process"], service_uuid=uuid())

    def test_list(self):
        hardware = self.client.ms("device", ["hardware", "list"])
        self.assert_dict_with_keys(hardware, ["start_pc"] + ELEMENT_TYPES)

        # test start pc config
        start_pc = hardware["start_pc"]
        self.assert_dict_with_keys(start_pc, ELEMENT_TYPES)
        for elem in ["mainboard", "powerPack", "case"]:
            self.assertIsInstance(start_pc[elem], str)
        for elem in ["cpu", "processorCooler", "gpu", "ram", "disk"]:
            self.assertIsInstance(start_pc[elem], list)

        # test mainboards
        self.assertIsInstance(hardware["mainboard"], dict)
        self.assertTrue(hardware["mainboard"])
        for mainboard in hardware["mainboard"].values():
            self.assert_dict_with_keys(
                mainboard,
                [
                    "id",
                    "case",
                    "cpuSocket",
                    "cpuSlots",
                    "coreTemperatureControl",
                    "usbPorts",
                    "ram",
                    "graphicUnitOnBoard",
                    "expansionSlots",
                    "diskStorage",
                    "networkPort",
                    "power",
                ],
            )

        # test processors
        self.assertIsInstance(hardware["cpu"], dict)
        self.assertTrue(hardware["cpu"])
        for cpu in hardware["cpu"].values():
            self.assert_dict_with_keys(
                cpu,
                [
                    "id",
                    "frequencyMin",
                    "frequencyMax",
                    "socket",
                    "cores",
                    "turboSpeed",
                    "overClock",
                    "maxTemperature",
                    "graphicUnit",
                    "power",
                ],
            )

        # test processor coolers
        self.assertIsInstance(hardware["processorCooler"], dict)
        self.assertTrue(hardware["processorCooler"])
        for cooler in hardware["processorCooler"].values():
            self.assert_dict_with_keys(cooler, ["id", "coolerSpeed", "socket", "power"])

        # test ram
        self.assertIsInstance(hardware["ram"], dict)
        self.assertTrue(hardware["ram"])
        for ram in hardware["ram"].values():
            self.assert_dict_with_keys(ram, ["id", "ramSize", "ramTyp", "frequency", "power"])

        # test gpu
        self.assertIsInstance(hardware["gpu"], dict)
        self.assertTrue(hardware["gpu"])
        for gpu in hardware["gpu"].values():
            self.assert_dict_with_keys(gpu, ["id", "ramSize", "ramTyp", "frequency", "interface", "power"])

        # test disk
        self.assertIsInstance(hardware["disk"], dict)
        self.assertTrue(hardware["disk"])
        for disk in hardware["disk"].values():
            self.assert_dict_with_keys(
                disk, ["id", "diskTyp", "capacity", "writingSpeed", "readingSpeed", "interface", "power"]
            )

        # test powerpack
        self.assertIsInstance(hardware["powerPack"], dict)
        self.assertTrue(hardware["powerPack"])
        for power_pack in hardware["powerPack"].values():
            self.assert_dict_with_keys(power_pack, ["id", "totalPower"])

        # test case
        self.assertIsInstance(hardware["case"], dict)
        self.assertTrue(hardware["case"])
        for case in hardware["case"].values():
            self.assert_dict_with_keys(case, ["id", "size"])
