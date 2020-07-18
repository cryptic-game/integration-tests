import time
from unittest.case import TestCase

from PyCrypCli.client import Client
from bcrypt import hashpw, gensalt

from database import execute
from util import get_client, is_uuid, uuid

super_uuid = uuid()
super_password = "Mcl?v&IFZ+1P%ZOj"
super_hash = hashpw(super_password.encode(), gensalt())


def clear_users():
    execute("DELETE FROM user")


def setup_account():
    clear_users()
    execute(
        "INSERT INTO user (uuid, created, name, password) VALUES (%s, current_timestamp, 'super', %s)",
        super_uuid,
        super_hash,
    )


def clear_sessions():
    execute("DELETE FROM session")


def setup_session() -> str:
    token = uuid()
    clear_sessions()
    execute(
        "INSERT INTO session (uuid, user, token, created, valid) VALUES (%s, %s, %s, current_timestamp, true)",
        uuid(),
        super_uuid,
        token,
    )
    return token


class TestServer(TestCase):
    def test_register_already_logged_in(self):
        setup_account()
        client: Client = get_client()
        client.login("super", super_password)

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
        actual = client.request({"action": "register", "name": "super", "password": super_password})
        self.assertEqual(expected, actual)

    def test_register_successful(self):
        clear_users()
        client: Client = get_client()
        client.init()

        result = client.request({"action": "register", "name": "super", "password": super_password})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))

    def test_login_already_logged_in(self):
        setup_account()
        client: Client = get_client()
        client.login("super", super_password)

        expected = {"error": "unknown action"}
        actual = client.request({"action": "login", "name": "super", "password": super_password})
        self.assertEqual(expected, actual)

    def test_login_invalid_credentials(self):
        clear_users()
        client: Client = get_client()
        client.init()

        expected = {"error": "permissions denied"}
        actual = client.request({"action": "login", "name": "super", "password": super_password})
        self.assertEqual(expected, actual)

    def test_login_successful(self):
        setup_account()
        client: Client = get_client()
        client.init()

        result = client.request({"action": "login", "name": "super", "password": super_password})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))

    def test_session_already_logged_in(self):
        setup_account()
        client: Client = get_client()
        client.login("super", super_password)

        expected = {"error": "unknown action"}
        actual = client.request({"action": "session", "token": uuid()})
        self.assertEqual(expected, actual)

    def test_session_invalid_token(self):
        clear_users()
        client: Client = get_client()
        client.init()

        expected = {"error": "invalid token"}
        actual = client.request({"action": "session", "token": uuid()})
        self.assertEqual(expected, actual)

    def test_session_successful(self):
        setup_account()
        token = setup_session()
        client: Client = get_client()
        client.init()

        expected = {"token": token}
        actual = client.request({"action": "session", "token": token})
        self.assertEqual(expected, actual)

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
        client.login("super", super_password)

        expected = {"status": "logout"}
        actual = client.request({"action": "logout"})
        self.assertEqual(expected, actual)

    def test_status_action(self):
        client: Client = get_client()
        client.init()

        result = client.request({"action": "status"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["online"], list(result))
        self.assertGreaterEqual(result["online"], 1)

    def test_info_action(self):
        setup_account()
        client: Client = get_client()
        client.login("super", super_password)

        result = client.request({"action": "info"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["created", "last", "name", "online", "uuid"], sorted(result))
        self.assertLess(abs(result["created"] / 1000 - time.time()), 10)
        self.assertLess(abs(result["last"] / 1000 - time.time()), 2)
        self.assertEqual("super", result["name"])
        self.assertGreaterEqual(result["online"], 1)
        self.assertEqual(super_uuid, result["uuid"])
