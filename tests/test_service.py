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
    WalletNotFoundException)

from database import execute
from testcase import TestCase
from tests.test_device import setup_device
from tests.test_server import setup_account, super_password, super_uuid
from util import get_client, uuid


def create_service(device=uuid(), name="telnet", n=1, part_owner=None, owner=super_uuid, clear_service=True):
    if clear_service:
        clear_services()

    service_uuids = []
    for i in range(n):
        service_uuids.append(uuid())
        execute("INSERT INTO service_service(uuid, device, owner, name, running,running_port, part_owner)" +
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                service_uuids[i],
                device,
                owner,
                name,
                i % 2 == 0,
                1337,
                part_owner
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
        actual = self.client.ms("service", ["public_info"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assert_dict_with_keys(actual, ["running_port", "name", "uuid", "device"])
        self.assertEqual(actual["device"], device_uuid)
        self.assertEqual(actual["uuid"], service_uuid)
        self.assertEqual(actual["running_port"], 1337)
        self.assertEqual(actual["name"], "telnet")

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
        service_uuid = create_service(device_uuids[0], "portscan")[0]
        service_uuid_target = create_service(device_uuids[2], clear_service=False)[0]
        actual = self.client.ms("service", ["use"], device_uuid=device_uuids[0], service_uuid=service_uuid,
                                target_device=device_uuids[2])
        self.assert_dict_with_keys(actual, ["services"])
        for service in actual["services"]:
            self.assertEqual(service["running_port"], 1337)
            self.assertEqual(service["name"], "telnet")
            self.assertEqual(service["uuid"], service_uuid_target)
            self.assertEqual(service["device"], device_uuids[2])

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
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid,
                           target_device=uuid())

    def test_use_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]
        service_uuid = create_service(device_uuid, owner=uuid(), name="portscan")[0]
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid, target_device=uuid())

    def test_use_service_cannot_be_used(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid)[0]
        with self.assertRaises(ServiceCannotBeUsedException):
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid, )

    def test_use_invalid_request(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid, "portscan")[0]
        with self.assertRaises(InvalidRequestException):
            self.client.ms("service", ["use"], device_uuid=device_uuid, service_uuid=service_uuid)

    def test_private_info_successful(self):
        device_uuid = setup_device()[0]
        service_uuid = create_service(device_uuid)[0]
        actual = self.client.ms("service", ["private_info"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assert_dict_with_keys(
            actual, ["running", "owner", "running_port", "name", "uuid", "device", "speed", "part_owner"])
        self.assertTrue(actual["running"])
        self.assertEqual(actual["owner"], super_uuid)
        self.assertEqual(actual["running_port"], 1337)
        self.assertEqual(actual["name"], "telnet")
        self.assertEqual(actual["uuid"], service_uuid)
        self.assertEqual(actual["device"], device_uuid)
        self.assertIsNone(actual["speed"])
        self.assertIsNone(actual["part_owner"])

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
        actual = self.client.ms("service", ["toggle"], device_uuid=device_uuid, service_uuid=service_uuid)
        self.assertFalse(actual["running"])
        self.assertEqual(actual["owner"],super_uuid)
        self.assertEqual(actual["running_port"],1337)
        self.assertEqual(actual["name"],"telnet")
        self.assertEqual(actual["uuid"],service_uuid)
        self.assertEqual(actual["device"],device_uuid)
        self.assertIsNone(actual["speed"])
        self.assertIsNone(actual["part_owner"])

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
        self.assertEqual(actual, expected)

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
            self.assertEqual(service["owner"], super_uuid)
            self.assertEqual(service["running_port"], 1337)
            self.assertEqual(service["name"], "telnet")
            self.assertIn(service["uuid"], service_uuids)
            self.assertEqual(service["device"], device_uuid)
            self.assertIsNone(service["speed"])
            self.assertIsNone(service["part_owner"])

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
        self.assertFalse(actual["running"])
        self.assertEqual(actual["owner"], super_uuid)
        self.assertEqual(actual["running_port"], 22)
        self.assertEqual(actual["name"], "ssh")
        self.assert_valid_uuid(actual["uuid"])
        self.assertEqual(actual["device"], device_uuid)
        self.assertEqual(actual["speed"], 0.0)
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
        _ = create_service(device_uuid, "ssh")
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
        _ = create_service(device_uuid, part_owner=super_uuid)[0]
        expected={"ok":True}
        actual = self.client.ms("service", ["part_owner"], device_uuid=device_uuid)
        self.assertEqual(expected,actual)

    def test_part_owner_no_access(self):
        device_uuid = setup_device(owner=uuid())[0]
        _ = create_service(device_uuid)[0]
        expected = {"ok": False}
        actual = self.client.ms("service", ["part_owner"], device_uuid=device_uuid)
        self.assertEqual(actual, expected)

    def test_part_owner_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("service", ["part_owner"], device_uuid=uuid())

    def test_part_owner_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("service", ["part_owner"], device_uuid=device_uuid)

    def test_list_part_owner_successful(self):
        service_uuids = create_service(uuid(), n=2, part_owner=super_uuid)
        actual = self.client.ms("service", ["list_part_owner"])
        self.assert_dict_with_keys(actual, ["services"])
        for service in actual["services"]:
            self.assertIsInstance(service["running"], bool)
            self.assert_valid_uuid(service["owner"])
            self.assertEqual(service["running_port"], 1337)
            self.assertEqual(service["name"], "telnet")
            self.assertIn(service["uuid"], service_uuids)
            self.assert_valid_uuid(service["device"])
            self.assertIsNone(service["speed"])
            self.assertEqual(service["part_owner"], super_uuid)
