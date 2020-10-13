from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    AlreadyMemberOfNetworkException,
    CannotKickOwnerException,
    CannotLeaveOwnNetworkException,
    DeviceNotOnlineException,
    InvalidNameException,
    InvitationAlreadyExistsException,
    MaximumNetworksReachedException,
    MicroserviceException,
    NameAlreadyInUseException,
    NetworkNotFoundException,
    NoPermissionsException,
)

from database import execute
from testcase import TestCase
from tests.test_device import setup_device
from tests.test_server import setup_account, super_password
from util import get_client, uuid


class InvitationNotFoundException(MicroserviceException):
    error: str = "invitation_not_found"


def create_network(owner, hidden=False, n=1):
    clear_networks()
    network_uuids = []
    for i in range(n):
        network_uuids.append(uuid())
        execute(
            "INSERT INTO network_network (uuid, hidden, name, owner) " "VALUES (%s, %s, %s, %s)",
            network_uuids[-1],
            hidden,
            f"test_network#{i + 1}",
            owner,
        )
    return network_uuids


def join_network(deviceuuid, networkuuid):
    execute("INSERT INTO network_member (uuid, device, network) VALUES (%s,%s,%s)", uuid(), deviceuuid, networkuuid)


def create_invitation(device, network, request=False):
    invitation_uuid = uuid()
    execute(
        "INSERT INTO network_invitation (uuid, device, network, request) VALUES (%s,%s,%s,%s)",
        invitation_uuid,
        device,
        network,
        request,
    )

    return invitation_uuid


def clear_networks():
    execute("TRUNCATE network_network")
    execute("TRUNCATE network_member")
    execute("TRUNCATE network_invitation")


class TestNetwork(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestNetwork"):
        cls.client.close()

    def test_name_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        expected = {"uuid": network_uuid, "hidden": False, "owner": device_uuid, "name": "test_network#1"}

        actual = self.client.ms("network", ["name"], name="test_network#1")
        self.assertEqual(actual, expected)

    def test_name_network_not_found(self):
        with self.assertRaises(NetworkNotFoundException):
            self.client.ms("network", ["name"], name="this network does not exists")

    def test_get_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        expected = {"uuid": network_uuid, "hidden": False, "owner": device_uuid, "name": "test_network#1"}

        actual = self.client.ms("network", ["get"], uuid=network_uuid)
        self.assertEqual(actual, expected)

    def test_get_network_not_found(self):
        with self.assertRaises(NetworkNotFoundException):
            self.client.ms("network", ["get"], uuid=uuid())

    def test_public_successful(self):
        device_uuid = setup_device()[0]
        network_uuids = create_network(device_uuid, False, 2)

        actual = self.client.ms("network", ["public"])
        self.assert_dict_with_keys(actual, ["networks"])
        for i in range(len(actual["networks"])):
            self.assertEqual(actual["networks"][i]["hidden"], False)
            self.assertEqual(actual["networks"][i]["owner"], device_uuid)
            self.assertIn(actual["networks"][i]["uuid"], network_uuids)
            self.assertIn(actual["networks"][i]["name"], [names["name"] for names in actual["networks"]])

    def test_create_successful(self):
        device_uuid = setup_device()[0]
        clear_networks()
        actual = self.client.ms("network", ["create"], device=device_uuid, name="new_network", hidden=False)
        self.assertIsInstance(actual, dict)
        self.assert_valid_uuid(actual["uuid"])
        self.assertFalse(actual["hidden"])
        self.assertEqual(actual["name"], "new_network")

    def test_create_max_network(self):
        device_uuid = setup_device()[0]
        _ = create_network(device_uuid, False, 3)
        with self.assertRaises(MaximumNetworksReachedException):
            self.client.ms("network", ["create"], device=device_uuid, name="new_network", hidden=False)

    def test_create_invalid_name(self):
        device_uuid = setup_device()[0]
        with self.assertRaises(InvalidNameException):
            self.client.ms("network", ["create"], device=device_uuid, name="space go brr", hidden=False)

    def test_create_name_already_used(self):
        device_uuid = setup_device()[0]
        _ = create_network(device_uuid)
        with self.assertRaises(NameAlreadyInUseException):
            self.client.ms("network", ["create"], device=device_uuid, name="test_network#1", hidden=False)

    def test_create_no_permission(self):
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["create"], device=uuid(), name="test_network#1", hidden=False)

    def test_create_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["create"], device=device_uuid, name="test_network#1", hidden=False)

    def test_members_successful(self):
        device_uuids = setup_device(2)
        network_uuid = create_network(device_uuids[0])[0]
        join_network(device_uuids[1], network_uuid)
        actual = self.client.ms("network", ["members"], uuid=network_uuid)
        self.assert_dict_with_keys(actual, ["members"])
        for member in actual["members"]:
            self.assertEqual(member["network"], network_uuid)
            self.assertIn(member["device"], device_uuids)
            self.assert_valid_uuid(member["uuid"])

    def test_members_network_not_found(self):
        with self.assertRaises(NetworkNotFoundException):
            self.client.ms("network", ["members"], uuid=uuid())

    def test_member_successful(self):
        device_uuid = setup_device()[0]
        network_uuids = create_network(device_uuid, n=2)
        join_network(device_uuid, network_uuids[0])
        join_network(device_uuid, network_uuids[0])
        actual = self.client.ms("network", ["member"], device=device_uuid)
        self.assert_dict_with_keys(actual, ["networks"])
        for network in actual["networks"]:
            self.assertEqual(network["owner"], device_uuid)
            self.assertFalse(network["hidden"])
            self.assertIn(network["uuid"], network_uuids)
            self.assertIsInstance(network["name"], str)

    def test_request_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(uuid())[0]
        actual = self.client.ms("network", ["request"], uuid=network_uuid, device=device_uuid)
        self.assert_dict_with_keys(actual, ["request", "uuid", "device", "network"])
        self.assertTrue(actual["request"])
        self.assert_valid_uuid(actual["uuid"])
        self.assertEqual(actual["device"], device_uuid)
        self.assertEqual(actual["network"], network_uuid)

    def test_request_network_not_found(self):
        with self.assertRaises(NetworkNotFoundException):
            self.client.ms("network", ["request"], uuid=uuid(), device=uuid())

    def test_request_already_member(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(uuid())[0]
        join_network(device_uuid, network_uuid)
        with self.assertRaises(AlreadyMemberOfNetworkException):
            self.client.ms("network", ["request"], uuid=network_uuid, device=device_uuid)

    def test_request_invitation_exists(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(uuid())[0]
        create_invitation(device_uuid, network_uuid, True)
        with self.assertRaises(InvitationAlreadyExistsException):
            self.client.ms("network", ["request"], uuid=network_uuid, device=device_uuid)

    def test_request_permission_denied(self):
        network_uuid = create_network(uuid())[0]
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["request"], uuid=network_uuid, device=uuid())

    def test_request_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        network_uuid = create_network(uuid())[0]
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["request"], uuid=network_uuid, device=device_uuid)

    def test_leave_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(uuid())[0]
        join_network(device_uuid, network_uuid)
        expected = {"result": True}
        actual = self.client.ms("network", ["leave"], uuid=network_uuid, device=device_uuid)
        self.assertEqual(actual, expected)

    def test_leave_permission_denied(self):
        network_uuid = create_network(uuid())[0]
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["leave"], uuid=network_uuid, device=uuid())

    def test_leave_not_in_network(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(uuid())[0]
        expected = {"result": False}
        actual = self.client.ms("network", ["leave"], uuid=network_uuid, device=device_uuid)
        self.assertEqual(actual, expected)

    def test_leave_owner_cannot_leave_network(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        with self.assertRaises(CannotLeaveOwnNetworkException):
            self.client.ms("network", ["leave"], uuid=network_uuid, device=device_uuid)

    def test_leave_device_not_online(self):
        device_uuid = setup_device(2)[1]
        network_uuid = create_network(uuid())[0]
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["leave"], uuid=network_uuid, device=device_uuid)

    def test_owner_successful(self):
        device_uuid = setup_device()[0]
        create_network(device_uuid)[0]
        actual = self.client.ms("network", ["owner"], device=device_uuid)
        self.assert_dict_with_keys(actual, ["networks"])
        for network in actual["networks"]:
            self.assertEqual(network["owner"], device_uuid)
            self.assertFalse(network["hidden"])
            self.assertIsInstance(network["name"], str)
            self.assert_valid_uuid(network["uuid"])

    def test_delete_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        expected = {"result": True}
        actual = self.client.ms("network", ["delete"], uuid=network_uuid)
        self.assertEqual(actual, expected)

    def test_delete_network_not_found(self):
        with self.assertRaises(NetworkNotFoundException):
            self.client.ms("network", ["delete"], uuid=uuid())

    def test_delete_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        network_uuid = create_network(device_uuid)[0]
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["delete"], uuid=network_uuid)

    def test_kick_successful(self):
        device_uuid = setup_device(3)
        network_uuid = create_network(device_uuid[0])[0]
        join_network(device_uuid[2], network_uuid)
        expected = {"result": True}
        actual = self.client.ms("network", ["kick"], uuid=network_uuid, device=device_uuid[2])
        self.assertEqual(actual, expected)

    def test_kick_permission_denied(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(uuid())[0]
        join_network(device_uuid, network_uuid)
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["kick"], uuid=network_uuid, device=device_uuid)

    def test_kick_not_in_network(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        expected = {"result": False}
        actual = self.client.ms("network", ["kick"], uuid=network_uuid, device=uuid())
        self.assertEqual(actual, expected)

    def test_kick_cannot_kick_owner(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        with self.assertRaises(CannotKickOwnerException):
            self.client.ms("network", ["kick"], uuid=network_uuid, device=device_uuid)

    def test_kick_device_powered_off(self):
        device_uuid = setup_device(2)
        network_uuid = create_network(device_uuid[1])[0]
        join_network(device_uuid[1], network_uuid)
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["kick"], uuid=network_uuid, device=device_uuid[0])

    def test_invite_successful(self):
        device_uuid = setup_device(3)
        network_uuid = create_network(device_uuid[0])[0]
        actual = self.client.ms("network", ["invite"], uuid=network_uuid, device=device_uuid[2])
        self.assert_dict_with_keys(actual, ["request", "uuid", "device", "network"])
        self.assertFalse(actual["request"])
        self.assert_valid_uuid(actual["uuid"])
        self.assertEqual(actual["device"], device_uuid[2])
        self.assertEqual(actual["network"], network_uuid)

    def test_invite_already_member(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        with self.assertRaises(AlreadyMemberOfNetworkException):
            self.client.ms("network", ["invite"], uuid=network_uuid, device=device_uuid)

    def test_invite_invitation_already_exists(self):
        device_uuid = setup_device(3)
        network_uuid = create_network(device_uuid[1])[0]
        create_invitation(device_uuid[2], network_uuid)
        with self.assertRaises(InvitationAlreadyExistsException):
            self.client.ms("network", ["invite"], uuid=network_uuid, device=device_uuid[2])

    def test_invite_network_not_found(self):
        device_uuid = setup_device()[0]
        with self.assertRaises(NetworkNotFoundException):
            self.client.ms("network", ["invite"], uuid=uuid(), device=device_uuid)

    def test_invite_device_not_online(self):
        network_uuid = create_network(uuid())[0]
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["invite"], uuid=network_uuid, device=uuid())

    def test_requests_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        create_invitation(uuid(), network_uuid, True)
        actual = self.client.ms("network", ["requests"], uuid=network_uuid)
        self.assert_dict_with_keys(actual, ["requests"])
        for request in actual["requests"]:
            self.assert_valid_uuid(request["uuid"])
            self.assertEqual(request["network"], network_uuid)
            self.assert_valid_uuid(request["device"])
            self.assertTrue(request["request"])

    def test_requests_permission_denied(self):
        network_uuid = create_network(uuid())[0]
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["requests"], uuid=network_uuid)

    def test_invitations_successful(self):
        device_uuid = setup_device()[0]
        create_invitation(device_uuid, uuid())
        actual = self.client.ms("network", ["invitations"], device=device_uuid)
        self.assert_dict_with_keys(actual, ["invitations"])
        for invitation in actual["invitations"]:
            self.assertFalse(invitation["request"])
            self.assertEqual(invitation["device"], device_uuid)
            self.assert_valid_uuid(invitation["uuid"])
            self.assert_valid_uuid(invitation["network"])

    def test_invitations_permission_denied(self):
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["invitations"], device=uuid())

    def test_invitations_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["invitations"], device=device_uuid)

    def test_network_invitations_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        create_invitation(uuid(), network_uuid)
        actual = self.client.ms("network", ["invitations", "network"], uuid=network_uuid)
        self.assert_dict_with_keys(actual, ["invitations"])
        for invitation in actual["invitations"]:
            self.assert_valid_uuid(invitation["uuid"])
            self.assertEqual(invitation["network"], network_uuid)
            self.assert_valid_uuid(invitation["device"])
            self.assertFalse(invitation["request"])

    def test_network_invitations_permission_denied(self):
        network_uuid = create_network(uuid())[0]
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["invitations", "network"], uuid=network_uuid)

    def test_revoke_successful(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]
        invitation_uuid = create_invitation(uuid(), network_uuid)
        expected = {"result": True}
        actual = self.client.ms("network", ["revoke"], uuid=invitation_uuid)
        self.assertEqual(actual, expected)

    def test_revoke_invitation_not_found(self):
        with self.assertRaises(InvitationNotFoundException):
            self.client.ms("network", ["revoke"], uuid=uuid())

    def test_revoke_permission_denied(self):
        network_uuid = create_network(uuid())[0]
        invitation_uuid = create_invitation(uuid(), network_uuid)
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["revoke"], uuid=invitation_uuid)

    def test_revoke_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        network_uuid = create_network(device_uuid)[0]
        invitation_uuid = create_invitation(uuid(), network_uuid)
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["revoke"], uuid=invitation_uuid)

    def test_accept_successful(self):
        device_uuid = setup_device()[0]
        invitation_uuid = create_invitation(device_uuid, uuid())
        expected = {"result": True}
        actual = self.client.ms("network", ["accept"], uuid=invitation_uuid)
        self.assertEqual(actual, expected)

    def test_accept_invitation_not_found(self):
        with self.assertRaises(InvitationNotFoundException):
            self.client.ms("network", ["accept"], uuid=uuid())

    def test_accept_permission_denied(self):
        invitation_uuid = create_invitation(uuid(), uuid())
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["accept"], uuid=invitation_uuid)

    def test_accept_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        invitation_uuid = create_invitation(device_uuid, uuid())
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["accept"], uuid=invitation_uuid)

    def test_deny_successful(self):
        device_uuid = setup_device()[0]
        invitation_uuid = create_invitation(device_uuid, uuid())
        expected = {"result": True}
        actual = self.client.ms("network", ["deny"], uuid=invitation_uuid)
        self.assertEqual(actual, expected)

    def test_deny_invitation_not_found(self):
        with self.assertRaises(InvitationNotFoundException):
            self.client.ms("network", ["deny"], uuid=uuid())

    def test_deny_permission_denied(self):
        invitation_uuid = create_invitation(uuid(), uuid())
        with self.assertRaises(NoPermissionsException):
            self.client.ms("network", ["deny"], uuid=invitation_uuid)

    def test_deny_device_powered_off(self):
        device_uuid = setup_device(2)[1]
        invitation_uuid = create_invitation(device_uuid, uuid())
        with self.assertRaises(DeviceNotOnlineException):
            self.client.ms("network", ["deny"], uuid=invitation_uuid)
