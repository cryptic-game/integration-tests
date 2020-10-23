from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    AttackNotRunningException,
    CouldNotStartService,
    DeviceNotFoundException,
    DeviceNotOnlineException,
    MicroserviceException,
    PermissionDeniedException,
    ServiceNotFoundException,
    ServiceNotRunningException,
)

from database import execute
from testcase import TestCase
from tests.test_device import setup_device
from tests.test_hardware import setup_workload
from tests.test_server import setup_account, super_password
from tests.test_service import create_service
from util import get_client, uuid


class AttackAlreadyRunning(MicroserviceException):
    error: str = "attack_already_running"


def create_bruteforce_service(service_uuid, target_device, target_service, started=False):
    clear_bruteforce_table()
    execute(
        "INSERT INTO service_bruteforce(uuid, started, target_service, target_device, progress) VALUES(%s,%s,%s,%s,%s)",
        service_uuid,
        started,
        target_service,
        target_device,
        1,
    )


def clear_bruteforce_table():
    execute("TRUNCATE service_bruteforce")


class TestBruteforce(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestBruteforce"):
        cls.client.close()

    def test_bruteforce_attack_successful(self):
        random_owner = uuid()
        device_uuid = setup_device()[0]
        setup_workload(device_uuid, clear_device=False)
        target_device = setup_device(owner=random_owner, clear_device=False)[0]
        service_uuid = create_service(device_uuid, name="bruteforce", n=2, speed=1.0)[1]
        target_service = create_service(target_device, clear_service=False, speed=1.0)[0]
        create_bruteforce_service(service_uuid, target_device, target_service, True)

        expected = {"ok": True}
        actual = self.client.ms(
            "service",
            ["bruteforce", "attack"],
            device_uuid=device_uuid,
            service_uuid=service_uuid,
            target_device=target_device,
            target_service=target_service,
        )
        self.assertEqual(expected, actual)

    def test_bruteforce_attack_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms(
                "service",
                ["bruteforce", "attack"],
                device_uuid=uuid(),
                service_uuid=uuid(),
                target_device=uuid(),
                target_service=uuid(),
            )

    def test_bruteforce_attack_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid, name="bruteforce", n=2, speed=0.0)[1]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms(
                "service",
                ["bruteforce", "attack"],
                device_uuid=device_uuid,
                service_uuid=service_uuid,
                target_device=uuid(),
                target_service=uuid(),
            )

    def test_bruteforce_attack_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid, name="bruteforce", n=2, speed=0.0)[1]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms(
                "service",
                ["bruteforce", "attack"],
                device_uuid=device_uuid,
                service_uuid=service_uuid,
                target_device=uuid(),
                target_service=uuid(),
            )

    def test_bruteforce_attack_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, name="bruteforce", n=2, speed=0.0)[1]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "service",
                ["bruteforce", "attack"],
                device_uuid=device_uuid,
                service_uuid=service_uuid,
                target_device=uuid(),
                target_service=uuid(),
            )

    def test_bruteforce_attack_service_not_running(self):
        device_uuid = setup_device()[0]
        target_device = setup_device(owner=uuid(), clear_device=False)[0]
        service_uuid = create_service(device_uuid, name="bruteforce", n=2, speed=1.0)[1]
        target_service = create_service(target_device, n=2, clear_service=False)[1]

        with self.assertRaises(ServiceNotRunningException):
            self.client.ms(
                "service",
                ["bruteforce", "attack"],
                device_uuid=device_uuid,
                service_uuid=service_uuid,
                target_device=target_device,
                target_service=target_service,
            )

    def test_bruteforce_attack_already_running(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, name="bruteforce", n=1, speed=1.0)[0]

        with self.assertRaises(AttackAlreadyRunning):
            self.client.ms(
                "service",
                ["bruteforce", "attack"],
                device_uuid=device_uuid,
                service_uuid=service_uuid,
                target_device=uuid(),
                target_service=uuid(),
            )

    def test_bruteforce_attack_could_not_start_service(self):
        device_uuid = setup_device()[0]
        target_device = setup_device(owner=uuid(), clear_device=False)[0]
        service_uuid = create_service(device_uuid, name="bruteforce", n=2, speed=1.0)[1]
        target_service = create_service(target_device, clear_service=False)[0]

        with self.assertRaises(CouldNotStartService):
            self.client.ms(
                "service",
                ["bruteforce", "attack"],
                device_uuid=device_uuid,
                service_uuid=service_uuid,
                target_device=target_device,
                target_service=target_service,
            )

    def test_bruteforce_status_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "bruteforce", speed=0.0)[0]
        create_bruteforce_service(service_uuid, uuid(), uuid(), True)

        actual = self.client.ms("service", ["bruteforce", "status"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assert_dict_with_keys(actual, ["uuid", "started", "target_device", "target_service", "progress"])
        self.assertEqual(service_uuid, actual["uuid"])
        self.assertEqual(1.0, actual["progress"])
        self.assert_valid_uuid(actual["target_device"])
        self.assert_valid_uuid(actual["target_service"])
        self.assertIsInstance(actual["started"], int)

    def test_bruteforce_status_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["bruteforce", "status"], device_uuid=uuid(), service_uuid=uuid())

    def test_bruteforce_status_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid, "bruteforce", speed=0.0)[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["bruteforce", "status"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_status_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid, "bruteforce", speed=0.0)[0]
        create_bruteforce_service(service_uuid, uuid(), uuid())

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["bruteforce", "status"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_status_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, "bruteforce", speed=0.0)[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["bruteforce", "status"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_status_attack_not_running(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "bruteforce", speed=0.0, n=2)[1]

        with self.assertRaises(AttackNotRunningException):
            self.client.ms("service", ["bruteforce", "status"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_stop_successful(self):
        device_uuid = setup_device()[0]
        target_device = setup_device(owner=uuid(), clear_device=False)[0]
        target_service = create_service(target_device)[0]
        service_uuid = create_service(device_uuid, "bruteforce", speed=2.0, clear_service=False)[0]
        create_bruteforce_service(service_uuid, target_device, target_service, True)

        actual = self.client.ms("service", ["bruteforce", "stop"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assertEqual(True, actual["ok"])
        self.assertEqual(target_device, actual["target_device"])
        self.assertIsInstance(actual["access"], bool)
        self.assertIsInstance(actual["progress"], float)

    def test_bruteforce_stop_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["bruteforce", "stop"], device_uuid=uuid(), service_uuid=uuid())

    def test_bruteforce_stop_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid, "bruteforce", speed=2.0, clear_service=False)[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["bruteforce", "stop"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_stop_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid, "bruteforce", speed=2.0, clear_service=False)[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["bruteforce", "stop"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_stop_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, "bruteforce", speed=2.0, clear_service=False)[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["bruteforce", "stop"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_stop_attack_not_running(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "bruteforce", speed=1.0, n=2)[1]

        with self.assertRaises(AttackNotRunningException):
            self.client.ms("service", ["bruteforce", "stop"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_bruteforce_stop_service_not_running(self):
        device_uuid = setup_device()[0]
        target_device = setup_device(owner=uuid(), clear_device=False)
        service_uuid = create_service(device_uuid, "bruteforce", speed=1.0)[0]
        target_service = create_service(target_device, n=2, clear_service=False)[1]
        create_bruteforce_service(service_uuid, target_device, target_service)

        with self.assertRaises(ServiceNotRunningException):
            self.client.ms("service", ["bruteforce", "stop"], device_uuid=device_uuid, service_uuid=service_uuid)
