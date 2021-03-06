from typing import List

from PyCrypCli.client import Client
from PyCrypCli.exceptions import (
    DeviceNotFoundException,
    DevicePoweredOffException,
    DirectoriesCanNotBeUpdatedException,
    DirectoryCanNotHaveTextContentException,
    FileAlreadyExistsException,
    FileNotFoundException,
    ParentDirectoryNotFound,
    PermissionDeniedException,
    CanNotMoveDirIntoItselfException,
)

from database import execute
from testcase import TestCase
from tests.test_device import setup_device
from tests.test_server import setup_account, super_password
from util import get_client, uuid


def create_files(device_uuids: List, n=1, is_directory=False, parent_uuid=None, clear_all_files=True) -> List[str]:
    if clear_all_files:
        clear_files()
    file_uuids = []
    for device in device_uuids:
        for i in range(n):
            file_uuid = uuid()
            if is_directory is False:
                content = f"test{i + 1}"
            else:
                content = ""
            execute(
                "INSERT INTO device_file(uuid, device,filename,content,is_directory,parent_dir_uuid) VALUES "
                + "(%s,%s,%s,%s,%s,%s)",
                file_uuid,
                device,
                f"test{i + 1}",
                content,
                is_directory,
                parent_uuid,
            )
            file_uuids.append(file_uuid)
    return file_uuids


def clear_files():
    execute("TRUNCATE device_file")


class TestFiles(TestCase):
    @classmethod
    def setUpClass(cls):
        setup_account()
        cls.client: Client = get_client()
        cls.client.login("super", super_password)

    @classmethod
    def tearDownClass(cls: "TestFiles"):
        cls.client.close()

    def test_info_file_successful(self):
        device_uuid = setup_device()
        file_uuid = create_files(device_uuid)[0]
        expected = {
            "is_directory": False,
            "filename": "test1",
            "parent_dir_uuid": None,
            "device": device_uuid[0],
            "uuid": file_uuid,
            "content": "test1",
        }
        actual = self.client.ms("device", ["file", "info"], device_uuid=device_uuid[0], file_uuid=file_uuid)
        self.assertEqual(expected, actual)

    def test_info_device_not_found(self):
        clear_files()
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["file", "info"], device_uuid=uuid(), file_uuid=uuid())

    def test_info_file_not_found(self):
        device_uuid = setup_device()
        with self.assertRaises(FileNotFoundException):
            self.client.ms("device", ["file", "info"], device_uuid=device_uuid[0], file_uuid=uuid())

    def test_info_device_powered_off(self):
        device_uuids = setup_device(2)
        file_uuid = create_files([device_uuids[1]])[0]
        with self.assertRaises(DevicePoweredOffException):
            self.client.ms("device", ["file", "info"], device_uuid=device_uuids[1], file_uuid=file_uuid)

    def test_info_permission_denied(self):
        other_device_uuid = setup_device(owner=uuid())[0]
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("device", ["file", "info"], device_uuid=other_device_uuid, file_uuid=uuid())

    def test_all_successful(self):
        device_uuid = setup_device()
        file_uuids = create_files(device_uuid, 5)
        result = self.client.ms("device", ["file", "all"], device_uuid=device_uuid[0], parent_dir_uuid=None)

        self.assert_dict_with_keys(result, ["files"])
        files = result["files"]
        for file in files:
            self.assert_dict_with_keys(
                file, ["is_directory", "filename", "parent_dir_uuid", "device", "uuid", "content"]
            )
            self.assertEqual(file["is_directory"], False)
            self.assertEqual(file["filename"][:4], "test")
            self.assertIsNone(file["parent_dir_uuid"])
            self.assertEqual(file["device"], device_uuid[0])
            self.assertIn(file["uuid"], file_uuids)
            self.assertEqual(file["content"][:4], "test")
            file_uuids.remove(file["uuid"])

    def test_all_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["file", "all"], device_uuid=uuid(), parent_dir_uuid=None)

    def test_all_device_powered_off(self):
        device_uuids = setup_device(2)[1]
        with self.assertRaises(DevicePoweredOffException):
            self.client.ms("device", ["file", "all"], device_uuid=device_uuids, parent_dir_uuid=None)

    def test_all_permission_denied(self):
        other_user_device_uuid = setup_device(1, uuid())[0]
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("device", ["file", "all"], device_uuid=other_user_device_uuid, parent_dir_uuid=None)

    def test_update_successful(self):
        device_uuid = setup_device()
        file_uuid = create_files(device_uuid)[0]
        expected = {
            "uuid": file_uuid,
            "device": device_uuid[0],
            "filename": "test1",
            "content": "new Content",
            "parent_dir_uuid": None,
            "is_directory": False,
        }
        actual = self.client.ms(
            "device", ["file", "update"], device_uuid=device_uuid[0], file_uuid=file_uuid, content="new Content"
        )
        self.assertEqual(actual, expected)

    def test_update_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["file", "update"], device_uuid=uuid(), file_uuid=uuid(), content="new Content")

    def test_update_file_not_found(self):
        device_uuid = setup_device()[0]
        with self.assertRaises(FileNotFoundException):
            self.client.ms(
                "device", ["file", "update"], device_uuid=device_uuid, file_uuid=uuid(), content="new Content"
            )

    def test_update_directories_not_updated(self):
        device_uuid = setup_device()
        file_uuid = create_files(device_uuid, is_directory=True)[0]
        with self.assertRaises(DirectoriesCanNotBeUpdatedException):
            self.client.ms(
                "device", ["file", "update"], device_uuid=device_uuid[0], file_uuid=file_uuid, content="new Content"
            )

    def test_update_powered_off(self):
        device_uuids = setup_device(2)
        with self.assertRaises(DevicePoweredOffException):
            self.client.ms(
                "device", ["file", "update"], device_uuid=device_uuids[1], file_uuid=uuid(), content="new Content"
            )

    def test_update_permission_denied(self):
        other_user_device_uuid = setup_device(1, uuid())[0]
        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "device",
                ["file", "update"],
                device_uuid=other_user_device_uuid,
                file_uuid=uuid(),
                content="new Content",
            )

    def test_delete_successful(self):
        device_uuid = setup_device()
        file_uuid = create_files(device_uuid)[0]
        actual = self.client.ms("device", ["file", "delete"], device_uuid=device_uuid[0], file_uuid=file_uuid)
        self.assertEqual({"ok": True}, actual)

    def test_delete_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms("device", ["file", "delete"], device_uuid=uuid(), file_uuid=uuid())

    def test_delete_file_not_found(self):
        device_uuid = setup_device()[0]
        with self.assertRaises(FileNotFoundException):
            self.client.ms("device", ["file", "delete"], device_uuid=device_uuid, file_uuid=uuid())

    def test_delete_permission_denied(self):
        other_user_device_uuid = setup_device(1, uuid())[0]
        with self.assertRaises(PermissionDeniedException):
            self.client.ms("device", ["file", "delete"], device_uuid=other_user_device_uuid, file_uuid=uuid())

    def test_delete_device_powered_off(self):
        device_uuid = setup_device(2)
        file_uuid = create_files([device_uuid[1]])[0]
        with self.assertRaises(DevicePoweredOffException):
            self.client.ms("device", ["file", "delete"], device_uuid=device_uuid[1], file_uuid=file_uuid)

    def test_create_successful(self):
        device_uuid = setup_device()[0]

        result = self.client.ms(
            "device",
            ["file", "create"],
            device_uuid=device_uuid,
            filename="new_file",
            content="its a file",
            parent_dir_uuid=None,
            is_directory=False,
        )

        self.assert_dict_with_keys(result, ["uuid", "device", "filename", "content", "parent_dir_uuid", "is_directory"])
        self.assert_valid_uuid(result["uuid"])
        self.assertEqual(result["device"], device_uuid)
        self.assertEqual(result["filename"], "new_file")
        self.assertEqual(result["content"], "its a file")
        self.assertIsNone(result["parent_dir_uuid"])
        self.assertFalse(result["is_directory"])

    def test_create_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms(
                "device",
                ["file", "create"],
                device_uuid=uuid(),
                filename="new_file",
                content="its a file",
                parent_dir_uuid=None,
                is_directory=False,
            )

    def test_create_permission_denied(self):
        device_uuid = setup_device(owner=uuid())[0]

        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "device",
                ["file", "create"],
                device_uuid=device_uuid,
                filename="new_file",
                content="its a file",
                parent_dir_uuid=None,
                is_directory=False,
            )

    def test_create_already_exists(self):
        device_uuid = setup_device()
        create_files(device_uuid)
        with self.assertRaises(FileAlreadyExistsException):
            self.client.ms(
                "device",
                ["file", "create"],
                device_uuid=device_uuid[0],
                filename="test1",
                content="its a file",
                parent_dir_uuid=None,
                is_directory=False,
            )

    def test_create_powered_off(self):
        device_uuid = setup_device(2)
        with self.assertRaises(DevicePoweredOffException):
            self.client.ms(
                "device",
                ["file", "create"],
                device_uuid=device_uuid[1],
                filename="test1",
                content="its a file",
                parent_dir_uuid=None,
                is_directory=False,
            )

    def test_create_parent_dir_not_found(self):
        device_uuid = setup_device()[0]
        with self.assertRaises(ParentDirectoryNotFound):
            self.client.ms(
                "device",
                ["file", "create"],
                device_uuid=device_uuid,
                filename="new_file",
                content="its a file",
                parent_dir_uuid=uuid(),
                is_directory=False,
            )

    def test_create_dir_cannot_have_content(self):
        device_uuid = setup_device()[0]
        with self.assertRaises(DirectoryCanNotHaveTextContentException):
            self.client.ms(
                "device",
                ["file", "create"],
                device_uuid=device_uuid,
                filename="new_file",
                content="its a file",
                parent_dir_uuid=None,
                is_directory=True,
            )

    def test_move_successful(self):
        device_uuid = setup_device()
        file_uuid = create_files(device_uuid)[0]
        directory_uuid = create_files(device_uuid, 1, True, None, False)[0]
        result = self.client.ms(
            "device",
            ["file", "move"],
            device_uuid=device_uuid[0],
            file_uuid=file_uuid,
            new_parent_dir_uuid=directory_uuid,
            new_filename="new_filename",
        )
        self.assert_dict_with_keys(result, ["is_directory", "filename", "parent_dir_uuid", "device", "uuid", "content"])
        self.assertFalse(result["is_directory"])
        self.assertEqual(result["filename"], "new_filename")
        self.assertEqual(result["parent_dir_uuid"], directory_uuid)
        self.assertEqual(result["device"], device_uuid[0])
        self.assertEqual(result["uuid"], file_uuid)
        self.assertEqual(result["content"], "test1")

    def test_move_device_not_found(self):
        with self.assertRaises(DeviceNotFoundException):
            self.client.ms(
                "device",
                ["file", "move"],
                device_uuid=uuid(),
                file_uuid=uuid(),
                new_parent_dir_uuid=uuid(),
                new_filename="new_filename",
            )

    def test_move_file_not_found(self):
        device_uuid = setup_device()
        with self.assertRaises(FileNotFoundException):
            self.client.ms(
                "device",
                ["file", "move"],
                device_uuid=device_uuid[0],
                file_uuid=uuid(),
                new_parent_dir_uuid=uuid(),
                new_filename="new_filename",
            )

    def test_move_file_already_exists(self):
        device_uuid = setup_device()

        file_uuid = create_files(device_uuid)[0]
        directory_uuid = create_files(device_uuid, 1, True, None, False)[0]
        create_files(device_uuid, 1, False, directory_uuid, False)
        with self.assertRaises(FileAlreadyExistsException):
            self.client.ms(
                "device",
                ["file", "move"],
                device_uuid=device_uuid[0],
                file_uuid=file_uuid,
                new_parent_dir_uuid=directory_uuid,
                new_filename="test1",
            )

    def test_move_permission_denied(self):
        other_user_device_uuid = setup_device(owner=uuid())
        with self.assertRaises(PermissionDeniedException):
            self.client.ms(
                "device",
                ["file", "move"],
                device_uuid=other_user_device_uuid[0],
                file_uuid=uuid(),
                new_parent_dir_uuid=uuid(),
                new_filename="test1",
            )

    def test_move_cannot_move_into_itself(self):
        device_uuid = setup_device()
        directory_uuid = create_files(device_uuid, 1, True)[0]
        with self.assertRaises(CanNotMoveDirIntoItselfException):
            self.client.ms(
                "device",
                ["file", "move"],
                device_uuid=device_uuid[0],
                file_uuid=directory_uuid,
                new_parent_dir_uuid=directory_uuid,
                new_filename="test1",
            )

    def test_move_parent_directory_not_found(self):
        device_uuid = setup_device()
        file_uuid = create_files(device_uuid)[0]
        with self.assertRaises(ParentDirectoryNotFound):
            self.client.ms(
                "device",
                ["file", "move"],
                device_uuid=device_uuid[0],
                file_uuid=file_uuid,
                new_parent_dir_uuid=uuid(),
                new_filename="test1",
            )

    def test_move_powered_off(self):
        device_uuid = setup_device(2)
        with self.assertRaises(DevicePoweredOffException):
            self.client.ms(
                "device",
                ["file", "move"],
                device_uuid=device_uuid[1],
                file_uuid=uuid(),
                new_parent_dir_uuid=uuid(),
                new_filename="new_filename",
            )
