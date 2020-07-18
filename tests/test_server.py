from unittest.case import TestCase

from PyCrypCli.client import Client

from database import execute
from util import get_client, is_uuid, uuid


class TestServer(TestCase):
    def test_register_invalid_password(self):
        execute("DELETE FROM user")
        client: Client = get_client()
        client.init()

        expected = {"error": "invalid password"}
        actual = client.request({"action": "register", "name": "super", "password": "foo"})
        self.assertEqual(expected, actual)

    def test_register_username_already_exists(self):
        execute("DELETE FROM user")
        execute("INSERT INTO user (uuid, name) VALUES (%s, 'super')", uuid())
        client: Client = get_client()
        client.init()

        expected = {"error": "username already exists"}
        actual = client.request({"action": "register", "name": "super", "password": "Super1234#"})
        self.assertEqual(expected, actual)

    def test_register_successful(self):
        execute("DELETE FROM user")
        client: Client = get_client()
        client.init()

        result = client.request({"action": "register", "name": "super", "password": "Super1234#"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))

    def test_login_failed(self):
        execute("DELETE FROM user")
        client: Client = get_client()
        client.init()

        expected = {"error": "permissions denied"}
        actual = client.request({"action": "login", "name": "super", "password": "Super1234#"})
        self.assertEqual(expected, actual)

    def test_login_successful(self):
        execute("DELETE FROM user")
        execute(
            "INSERT INTO user (uuid, name, password) VALUES (%s, 'super', %s)",
            uuid(),
            "$2a$12$qjj2fvAdX52pGZjWtbPnfOo0v5xqxZUTAoA7Ubbn1M/DF5QNJloLi",  # Super1234#
        )
        client: Client = get_client()
        client.init()

        result = client.request({"action": "login", "name": "super", "password": "Super1234#"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))
