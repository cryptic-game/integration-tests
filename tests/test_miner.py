from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    CouldNotStartService,
    DeviceNotFoundException,
    DeviceNotOnlineException,
    PermissionDeniedException,
    ServiceNotFoundException,
    WalletNotFoundException,
)

from database import execute
from testcase import TestCase
from tests.test_device import setup_device
from tests.test_hardware import setup_workload
from tests.test_server import setup_account, super_password, super_uuid
from tests.test_service import create_service
from tests.test_shop import create_wallet
from util import get_client, uuid


def create_miner_service(service_uuid, wallet_uuid=None, started=False, power=0.0):
    clear_miner_service()
    execute(
        "INSERT INTO service_miner (uuid, wallet, started, power) VALUES (%s,%s,%s,%s)",
        service_uuid,
        wallet_uuid,
        started,
        power,
    )


def clear_miner_service():
    execute("TRUNCATE service_miner")


class TestMiner(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestMiner"):
        cls.client.close()

    def test_miner_get_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "miner")[0]
        create_miner_service(service_uuid)

        expected = {"wallet": None, "started": 0, "power": 0.0, "uuid": service_uuid}
        actual = self.client.ms("service", ["miner", "get"], service_uuid=service_uuid)
        self.assertEqual(expected, actual)

    def test_miner_get_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["miner", "get"], service_uuid=uuid())

    def test_miner_get_device_not_found(self):
        service_uuid = create_service(uuid(), "miner")[0]
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["miner", "get"], service_uuid=service_uuid)

    def test_miner_get_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["miner", "get"], service_uuid=service_uuid)

    def test_miner_get_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["miner", "get"], service_uuid=service_uuid)

    def test_miner_list_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "miner")[0]
        wallet_uuid = create_wallet()[0]
        create_miner_service(service_uuid, wallet_uuid)

        expected = {
            "miners": [
                {
                    "service": {
                        "running": True,
                        "owner": super_uuid,
                        "running_port": 1337,
                        "name": "miner",
                        "uuid": service_uuid,
                        "device": device_uuid,
                        "part_owner": None,
                        "speed": None,
                    },
                    "miner": {"wallet": wallet_uuid, "started": 0, "power": 0.0, "uuid": service_uuid},
                }
            ]
        }
        actual = self.client.ms("service", ["miner", "list"], wallet_uuid=wallet_uuid)
        self.assertEqual(expected, actual)

    def test_miner_wallet(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "miner", speed=1.0)[0]
        create_miner_service(service_uuid)
        wallet_uuid = create_wallet()[0]

        actual = self.client.ms("service", ["miner", "wallet"], service_uuid=service_uuid, wallet_uuid=wallet_uuid)
        self.assertEqual(wallet_uuid, actual["wallet"])
        self.assertEqual(0.0, actual["power"])
        self.assertEqual(service_uuid, actual["uuid"])
        self.assertIsInstance(actual["started"], int)

    def test_miner_wallet_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["miner", "wallet"], service_uuid=uuid(), wallet_uuid=uuid())

    def test_miner_wallet_device_not_found(self):
        service_uuid = create_service(uuid(), "miner")[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["miner", "wallet"], service_uuid=service_uuid, wallet_uuid=uuid())

    def test_miner_wallet_device_not_online(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["miner", "wallet"], service_uuid=service_uuid, wallet_uuid=uuid())

    def test_miner_wallet_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["miner", "wallet"], service_uuid=service_uuid, wallet_uuid=uuid())

    def test_miner_wallet_not_found(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(WalletNotFoundException):
            self.client.ms("service", ["miner", "wallet"], service_uuid=service_uuid, wallet_uuid=uuid())

    def test_miner_power_successful(self):
        device_uuid = setup_device()[0]
        setup_workload(device_uuid, False)
        service_uuid = create_service(device_uuid, "miner", n=2)[1]
        wallet_uuid = create_wallet()[0]
        create_miner_service(service_uuid, wallet_uuid, False, 1)

        actual = self.client.ms("service", ["miner", "power"], service_uuid=service_uuid, power=1.0)
        self.assertEqual(service_uuid, actual["uuid"])
        self.assertEqual(wallet_uuid, actual["wallet"])
        self.assertEqual(1.0, actual["power"])
        self.assertIsInstance(actual["started"], int)

    def test_miner_power_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["miner", "power"], service_uuid=uuid(), power=0.5)

    def test_miner_power_device_not_found(self):
        service_uuid = create_service(uuid(), "miner")[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["miner", "power"], service_uuid=service_uuid, power=0.5)

    def test_miner_power_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["miner", "power"], service_uuid=service_uuid, power=0.5)

    def test_miner_power_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["miner", "power"], service_uuid=service_uuid, power=0.5)

    def test_miner_power_wallet_not_found(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "miner")[0]
        create_miner_service(service_uuid, uuid())

        with self.assertRaises(WalletNotFoundException):
            self.client.ms("service", ["miner", "power"], service_uuid=service_uuid, power=0.5)

    def test_miner_power_could_not_start_service(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "miner", speed=1)[0]
        wallet_uuid = create_wallet()[0]
        create_miner_service(service_uuid, wallet_uuid)

        with self.assertRaises(CouldNotStartService):
            self.client.ms("service", ["miner", "power"], service_uuid=service_uuid, power=0.5)
