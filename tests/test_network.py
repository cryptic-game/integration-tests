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


def create_network(owner, n=1):
    clear_networks()
    network_uuids = []
    for i in range(n):
        network_uuids.append(uuid())
        execute(
            "INSERT INTO network_network (uuid, hidden, name, owner) VALUES (%s, %s, %s, %s)",
            network_uuids[-1],
            bool(i % 2),
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
            self.client.ms("network", ["name"], name=uuid())

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
        network_uuids = create_network(device_uuid, 4)
        names = {network_uuid: f"test_network#{i + 1}" for i, network_uuid in enumerate(network_uuids) if not i % 2}

        actual = self.client.ms("network", ["public"])
        self.assert_dict_with_keys(actual, ["networks"])
        networks = actual["networks"]
        self.assertEqual(2, len(networks))
        for network in networks:
            self.assert_dict_with_keys(network, ["uuid", "hidden", "owner", "name"])
            self.assertEqual(False, network["hidden"])
            self.assertEqual(device_uuid, network["owner"])
            self.assertIn(network["uuid"], names)
            self.assertEqual(names[network["uuid"]], network["name"])
            names.pop(network["uuid"])
        self.assertFalse(names)

    def test_create_successful(self):
        device_uuid = setup_device()[0]
        clear_networks()

        actual = self.client.ms("network", ["create"], device=device_uuid, name="new_network", hidden=False)
        self.assert_dict_with_keys(actual, ["uuid", "hidden", "owner", "name"])
        self.assert_valid_uuid(actual["uuid"])
        self.assertFalse(actual["hidden"])
        self.assertEqual("new_network", actual["name"])
        self.assertEqual(device_uuid, actual["owner"])

    def test_create_max_network(self):
        device_uuid = setup_device()[0]
        create_network(device_uuid, 2)
        with self.assertRaises(MaximumNetworksReachedException):
            self.client.ms("network", ["create"], device=device_uuid, name="new_network", hidden=False)

    def test_create_invalid_name(self):
        device_uuid = setup_device()[0]
        with self.assertRaises(InvalidNameException):
            self.client.ms("network", ["create"], device=device_uuid, name="space go brr", hidden=False)

    def test_create_name_already_used(self):
        device_uuid = setup_device()[0]
        create_network(device_uuid)
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
        device_uuids = setup_device(5)
        network_uuid = create_network(device_uuids[0])[0]
        uuids = set()
        for i in range(0, 5, 2):
            uuids.add(device_uuids[i])
            join_network(device_uuids[i], network_uuid)

        actual = self.client.ms("network", ["members"], uuid=network_uuid)
        self.assert_dict_with_keys(actual, ["members"])
        self.assertEqual(3, len(actual["members"]))
        for member in actual["members"]:
            self.assert_dict_with_keys(member, ["uuid", "network", "device"])
            self.assertEqual(network_uuid, member["network"])
            self.assertIn(member["device"], uuids)
            uuids.remove(member["device"])
            self.assert_valid_uuid(member["uuid"])
        self.assertFalse(uuids)

    def test_members_network_not_found(self):
        with self.assertRaises(NetworkNotFoundException):
            self.client.ms("network", ["members"], uuid=uuid())

    def test_member_successful(self):
        device_uuid = setup_device()[0]
        network_uuids = create_network(device_uuid, n=4)
        indices = {}
        for i in range(0, 4, 2):
            indices[network_uuids[i]] = i
            join_network(device_uuid, network_uuids[i])

        actual = self.client.ms("network", ["member"], device=device_uuid)
        self.assert_dict_with_keys(actual, ["networks"])
        self.assertEqual(2, len(actual["networks"]))
        for network in actual["networks"]:
            self.assert_dict_with_keys(network, ["owner", "hidden", "uuid", "name"])
            self.assertEqual(network["owner"], device_uuid)
            self.assertIn(network["uuid"], indices)
            i = indices.pop(network["uuid"])
            self.assertIs(bool(i % 2), network["hidden"])
            self.assertEqual(network["name"], f"test_network#{i + 1}")
        self.assertFalse(indices)

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
        create_network(device_uuid)

        actual = self.client.ms("network", ["owner"], device=device_uuid)
        self.assert_dict_with_keys(actual, ["networks"])
        self.assertEqual(1, len(actual["networks"]))

        network = actual["networks"][0]
        self.assert_dict_with_keys(network, ["owner", "hidden", "name", "uuid"])
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
        device_uuids = setup_device(3)
        network_uuid = create_network(device_uuids[0])[0]

        actual = self.client.ms("network", ["invite"], uuid=network_uuid, device=device_uuids[2])
        self.assert_dict_with_keys(actual, ["request", "uuid", "device", "network"])
        self.assertFalse(actual["request"])
        self.assert_valid_uuid(actual["uuid"])
        self.assertEqual(actual["device"], device_uuids[2])
        self.assertEqual(actual["network"], network_uuid)

    def test_invite_already_member(self):
        device_uuid = setup_device()[0]
        network_uuid = create_network(device_uuid)[0]

        with self.assertRaises(AlreadyMemberOfNetworkException):
            self.client.ms("network", ["invite"], uuid=network_uuid, device=device_uuid)

    def test_invite_invitation_already_exists(self):
        device_uuids = setup_device(3)
        network_uuid = create_network(device_uuids[1])[0]
        create_invitation(device_uuids[2], network_uuid)

        with self.assertRaises(InvitationAlreadyExistsException):
            self.client.ms("network", ["invite"], uuid=network_uuid, device=device_uuids[2])

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
        self.assertEqual(1, len(actual["requests"]))

        request = actual["requests"][0]
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
        self.assertEqual(1, len(actual["invitations"]))

        invitation = actual["invitations"][0]
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
        self.assertEqual(1, len(actual["invitations"]))

        invitation = actual["invitations"][0]
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
