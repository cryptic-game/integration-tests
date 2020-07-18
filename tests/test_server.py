from unittest.case import TestCase

from PyCrypCli.client import Client

from database import execute
from util import get_client, is_uuid, uuid


def clear_users():
    execute("DELETE FROM user")


def setup_account():
    clear_users()
    execute(
        "INSERT INTO user (uuid, created, name, password) VALUES (%s, current_timestamp, 'super', %s)",
        uuid(),
        "$2a$12$qjj2fvAdX52pGZjWtbPnfOo0v5xqxZUTAoA7Ubbn1M/DF5QNJloLi",  # Super1234#
    )


class TestServer(TestCase):
    def test_register_already_logged_in(self):
        setup_account()
        client: Client = get_client()
        client.login("super", "Super1234#")

        expected = {"error": "unknown action"}
        actual = client.request({"action": "register", "name": "super", "password": "foo"})
        self.assertEqual(expected, actual)

    def test_register_invalid_password(self):
        clear_users()
        client: Client = get_client()
        client.init()

        expected = {"error": "invalid password"}
        actual = client.request({"action": "register", "name": "super", "password": "foo"})
        self.assertEqual(expected, actual)

    def test_register_username_already_exists(self):
        setup_account()
        client: Client = get_client()
        client.init()

        expected = {"error": "username already exists"}
        actual = client.request({"action": "register", "name": "super", "password": "Super1234#"})
        self.assertEqual(expected, actual)

    def test_register_successful(self):
        clear_users()
        client: Client = get_client()
        client.init()

        result = client.request({"action": "register", "name": "super", "password": "Super1234#"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))

    def test_login_already_logged_in(self):
        setup_account()
        client: Client = get_client()
        client.login("super", "Super1234#")

        expected = {"error": "unknown action"}
        actual = client.request({"action": "login", "name": "super", "password": "Super1234#"})
        self.assertEqual(expected, actual)

    def test_login_invalid_credentials(self):
        clear_users()
        client: Client = get_client()
        client.init()

        expected = {"error": "permissions denied"}
        actual = client.request({"action": "login", "name": "super", "password": "Super1234#"})
        self.assertEqual(expected, actual)

    def test_login_successful(self):
        setup_account()
        client: Client = get_client()
        client.init()

        result = client.request({"action": "login", "name": "super", "password": "Super1234#"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))

    def test_logout_failed(self):
        setup_account()
        client: Client = get_client()
        client.init()

        expected = {"error": "unknown action"}
        actual = client.request({"action": "logout"})
        self.assertEqual(expected, actual)

    def test_logout_successful(self):
        setup_account()
        client: Client = get_client()
        client.login("super", "Super1234#")

        expected = {"status": "logout"}
        actual = client.request({"action": "logout"})
        self.assertEqual(expected, actual)
