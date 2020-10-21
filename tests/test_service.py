from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    AlreadyOwnThisServiceException,
    CannotDeleteEnforcedServiceException,
    CannotToggleDirectlyException,
    CouldNotStartService,
    DeviceNotFoundException,
    DeviceNotOnlineException,
    InvalidRequestException,
    PermissionDeniedException,
    ServiceCannotBeUsedException,
    ServiceNotFoundException,
    ServiceNotSupportedException,
    WalletNotFoundException,
)

from database import execute
from testcase import TestCase
from tests.test_device import setup_device
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, uuid


def create_service(device, name="telnet", n=1, part_owner=None, owner=super_uuid, speed=None, clear_service=True):
    if clear_service:
        clear_services()

    service_uuids = []
    for i in range(n):
        service_uuids.append(uuid())
        execute(
            "INSERT INTO service_service (uuid, device, owner, name, running, running_port, part_owner, speed) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            service_uuids[i],
            device,
            owner,
            name,
            i % 2 == 0,
            1337,
            part_owner,
            speed,
        )

    return service_uuids


def clear_services():
    execute("TRUNCATE service_service")


class TestService(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestService"):
        cls.client.close()

    def test_public_info_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid)[0]

        expected = {"device": device_uuid, "uuid": service_uuid, "running_port": 1337, "name": "telnet"}
        actual = self.client.ms("service", ["public_info"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assertEqual(expected, actual)

    def test_public_info_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["public_info"], device_uuid=uuid(), service_uuid=uuid())

    def test_public_info_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["public_info"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_public_info_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["public_info"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_use_successful(self):
        device_uuids = setup_device(3)
        service_uuid = create_service(device_uuids[0], name="portscan")[0]
        service_uuid_target = create_service(device_uuids[2], clear_service=False)[0]

        expected = {
            "services": [
                {"device": device_uuids[2], "uuid": service_uuid_target, "running_port": 1337, "name": "telnet"}
            ]
        }
        actual = self.client.ms(
            "service", ["use"], device_uuid=device_uuids[0], service_uuid=service_uuid, target_device=device_uuids[2]
        )
        self.assertEqual(expected, actual)

    def test_use_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["use"], device_uuid=uuid(), service_uuid=uuid())

    def test_use_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_use_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid, name="portscan")[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid, target_device=uuid())

    def test_use_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, owner=uuid(), name="portscan")[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid, target_device=uuid())

    def test_use_service_cannot_be_used(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, name="telnet")[0]

        with self.assertRaises(ServiceCannotBeUsedException):
            self.client.ms(
                "service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid,
            )

    def test_use_invalid_request(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "portscan")[0]

        with self.assertRaises(InvalidRequestException):
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_private_info_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid)[0]

        expected = {
            "running": True,
            "owner": super_uuid,
            "running_port": 1337,
            "name": "telnet",
            "uuid": service_uuid,
            "device": device_uuid,
            "speed": None,
            "part_owner": None,
        }
        actual = self.client.ms("service", ["private_info"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assertEqual(expected, actual)

    def test_private_info_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["private_info"], device_uuid=uuid(), service_uuid=uuid())

    def test_private_info_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["private_info"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_private_info_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["private_info"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_private_info_permission_denied(self):
        device_uuid = setup_device(1, uuid())[0]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["private_info"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_toggle_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid)[0]

        expected = {
            "running": False,
            "owner": super_uuid,
            "running_port": 1337,
            "name": "telnet",
            "uuid": service_uuid,
            "device": device_uuid,
            "speed": None,
            "part_owner": None,
        }
        actual = self.client.ms("service", ["toggle"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assertEqual(expected, actual)

    def test_toggle_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["toggle"], device_uuid=uuid(), service_uuid=uuid())

    def test_toggle_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["toggle"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_toggle_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["toggle"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_toggle_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["toggle"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_toggle_cannot_toggle_directly(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "miner")[0]

        with self.assertRaises(CannotToggleDirectlyException):
            self.client.ms("service", ["toggle"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_toggle_could_not_start_service(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "telnet", n=2)[1]

        with self.assertRaises(CouldNotStartService):
            self.client.ms("service", ["toggle"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_delete_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid)[0]

        expected = {"ok": True}
        actual = self.client.ms("service", ["delete"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assertEqual(expected, actual)

    def test_delete_service_not_found(self):
        with self.assertRaises(ServiceNotFoundException):
            self.client.ms("service", ["delete"], device_uuid=uuid(), service_uuid=uuid())

    def test_delete_device_not_found(self):
        device_uuid = uuid()
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["delete"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_delete_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["delete"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_delete_enforced_service(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "ssh")[0]

        with self.assertRaises(CannotDeleteEnforcedServiceException):
            self.client.ms("service", ["delete"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_delete_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid)[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["delete"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_list_successful(self):
        device_uuid = setup_device()[0]
        service_uuids = create_service(device_uuid, n=2)

        actual = self.client.ms("service", ["list"], device_uuid=device_uuid)
        self.assert_dict_with_keys(actual, ["services"])
        for service in actual["services"]:
            self.assertIsInstance(service["running"], bool)
            self.assertEqual(super_uuid, service["owner"])
            self.assertEqual(1337, service["running_port"])
            self.assertEqual("telnet", service["name"])
            self.assertEqual(device_uuid, service["device"])
            self.assertIsNone(service["speed"])
            self.assertIsNone(service["part_owner"])
            self.assertIn(service["uuid"], service_uuids)

    def test_list_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["list"], device_uuid=uuid())

    def test_list_device_powered_off(self):
        device_uuid = setup_device(2)[1]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["list"], device_uuid=device_uuid)

    def test_list_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["list"], device_uuid=device_uuid)

    def test_create_successful(self):
        device_uuid = setup_device()[0]

        actual = self.client.ms("service", ["create"], device_uuid=device_uuid, name="ssh")
        self.assert_dict_with_keys(
            actual, ["uuid", "device", "owner", "name", "running", "running_port", "part_owner", "speed"]
        )
        self.assert_valid_uuid(actual["uuid"])
        self.assertFalse(actual["running"])
        self.assertEqual(super_uuid, actual["owner"])
        self.assertEqual(22, actual["running_port"])
        self.assertEqual("ssh", actual["name"])
        self.assertEqual(device_uuid, actual["device"])
        self.assertEqual(0.0, actual["speed"])
        self.assertIsNone(actual["part_owner"])

    def test_create_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["create"], device_uuid=uuid(), name="ssh")

    def test_create_device_powered_off(self):
        device_uuid = setup_device(2)[1]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["create"], device_uuid=device_uuid, name="ssh")

    def test_create_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["create"], device_uuid=device_uuid, name="ssh")

    def test_create_service_not_supported(self):
        device_uuid = setup_device()[0]

        with self.assertRaises(ServiceNotSupportedException):
            self.client.ms("service", ["create"], device_uuid=device_uuid, name="nothing here")

    def test_create_service_already_exists(self):
        device_uuid = setup_device()[0]
        create_service(device_uuid, "ssh")

        with self.assertRaises(AlreadyOwnThisServiceException):
            self.client.ms("service", ["create"], device_uuid=device_uuid, name="ssh")

    def test_create_wallet_not_found(self):
        device_uuid = setup_device()[0]

        with self.assertRaises(WalletNotFoundException):
            self.client.ms("service", ["create"], device_uuid=device_uuid, name="miner", wallet_uuid=uuid())

    def test_create_invalid_request(self):
        device_uuid = setup_device()[0]

        with self.assertRaises(InvalidRequestException):
            self.client.ms("service", ["create"], device_uuid=device_uuid, name="miner")

    def test_part_owner_access(self):
        device_uuid = setup_device(owner=uuid())[0]
        create_service(device_uuid, part_owner=super_uuid)

        expected = {"ok": True}
        actual = self.client.ms("service", ["part_owner"], device_uuid=device_uuid)
        self.assertEqual(expected, actual)

    def test_part_owner_no_access(self):
        device_uuid = setup_device(owner=uuid())[0]
        create_service(device_uuid)

        expected = {"ok": False}
        actual = self.client.ms("service", ["part_owner"], device_uuid=device_uuid)
        self.assertEqual(expected, actual)

    def test_part_owner_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["part_owner"], device_uuid=uuid())

    def test_part_owner_device_powered_off(self):
        device_uuid = setup_device(2)[1]

        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["part_owner"], device_uuid=device_uuid)

    def test_list_part_owner_successful(self):
        device_uuid = uuid()
        service_uuids = create_service(device_uuid, n=2, part_owner=super_uuid)

        actual = self.client.ms("service", ["list_part_owner"])
        self.assert_dict_with_keys(actual, ["services"])
        for service in actual["services"]:
            self.assertIsInstance(service["running"], bool)
            self.assert_valid_uuid(service["owner"])
            self.assertEqual(device_uuid, service["device"])
            self.assertEqual(super_uuid, service["part_owner"])
            self.assertEqual(1337, service["running_port"])
            self.assertEqual("telnet", service["name"])
            self.assertIsNone(service["speed"])
            self.assertIn(service["uuid"], service_uuids)
