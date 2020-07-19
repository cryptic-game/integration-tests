import time
from unittest.case import TestCase

from PyCrypCli.client import Client
from PyCrypCli.exceptions import InvalidLoginException
from bcrypt import hashpw, gensalt

from database import execute
from util import get_client, is_uuid, uuid

super_uuid = uuid()
super_password = "Mcl?v&IFZ+1P%ZOj"
super_hash = hashpw(super_password.encode(), gensalt())


def clear_users():
    execute("TRUNCATE user")


def setup_account():
    clear_users()
    execute(
        "INSERT INTO user (uuid, created, name, password) VALUES (%s, current_timestamp, 'super', %s)",
        super_uuid,
        super_hash,
    )


def clear_sessions():
    execute("TRUNCATE session")


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
    def setUp(self):
        self.client: Client = get_client()

    def tearDown(self):
        self.client.close()

    def test_register_already_logged_in(self):
        setup_account()
        self.client.login("super", super_password)

        expected = {"error": "unknown action"}
        actual = self.client.request({"action": "register", "name": "super", "password": "foo"})
        self.assertEqual(expected, actual)

    def test_register_invalid_password(self):
        clear_users()
        self.client.init()

        expected = {"error": "invalid password"}
        actual = self.client.request({"action": "register", "name": "super", "password": "foo"})
        self.assertEqual(expected, actual)

    def test_register_username_already_exists(self):
        setup_account()
        self.client.init()

        expected = {"error": "username already exists"}
        actual = self.client.request({"action": "register", "name": "super", "password": super_password})
        self.assertEqual(expected, actual)

    def test_register_successful(self):
        clear_users()
        self.client.init()

        result = self.client.request({"action": "register", "name": "super", "password": super_password})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))

    def test_login_already_logged_in(self):
        setup_account()
        self.client.login("super", super_password)

        expected = {"error": "unknown action"}
        actual = self.client.request({"action": "login", "name": "super", "password": super_password})
        self.assertEqual(expected, actual)

    def test_login_invalid_credentials(self):
        clear_users()
        self.client.init()

        expected = {"error": "permissions denied"}
        actual = self.client.request({"action": "login", "name": "super", "password": super_password})
        self.assertEqual(expected, actual)

    def test_login_successful(self):
        setup_account()
        self.client.init()

        result = self.client.request({"action": "login", "name": "super", "password": super_password})
        self.assertIsInstance(result, dict)
        self.assertEqual(["token"], list(result))
        self.assertTrue(is_uuid(result["token"]))

    def test_session_already_logged_in(self):
        setup_account()
        self.client.login("super", super_password)

        expected = {"error": "unknown action"}
        actual = self.client.request({"action": "session", "token": uuid()})
        self.assertEqual(expected, actual)

    def test_session_invalid_token(self):
        clear_users()
        self.client.init()

        expected = {"error": "invalid token"}
        actual = self.client.request({"action": "session", "token": uuid()})
        self.assertEqual(expected, actual)

    def test_session_successful(self):
        setup_account()
        token = setup_session()
        self.client.init()

        expected = {"token": token}
        actual = self.client.request({"action": "session", "token": token})
        self.assertEqual(expected, actual)

    def test_logout_failed(self):
        setup_account()
        self.client.init()

        expected = {"error": "unknown action"}
        actual = self.client.request({"action": "logout"})
        self.assertEqual(expected, actual)

    def test_logout_successful(self):
        setup_account()
        self.client.login("super", super_password)

        expected = {"status": "logout"}
        actual = self.client.request({"action": "logout"})
        self.assertEqual(expected, actual)

    def test_status_action(self):
        self.client.init()

        result = self.client.request({"action": "status"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["online"], list(result))
        self.assertGreaterEqual(result["online"], 1)

    def test_info_action(self):
        setup_account()
        self.client.login("super", super_password)

        result = self.client.request({"action": "info"})
        self.assertIsInstance(result, dict)
        self.assertEqual(["created", "last", "name", "online", "uuid"], sorted(result))
        self.assertLess(abs(result["created"] / 1000 - time.time()), 10)
        self.assertLess(abs(result["last"] / 1000 - time.time()), 2)
        self.assertEqual("super", result["name"])
        self.assertGreaterEqual(result["online"], 1)
        self.assertEqual(super_uuid, result["uuid"])

    def test_password_logged_in(self):
        setup_account()
        self.client.login("super", super_password)

        expected = {"error": "unknown action"}
        actual = self.client.request({"action": "password", "name": "super", "password": super_password, "new": "x"})
        self.assertEqual(expected, actual)

    def test_password_invalid_credentials(self):
        clear_users()
        self.client.init()

        expected = {"error": "permissions denied"}
        actual = self.client.request(
            {"action": "password", "name": "super", "password": super_password, "new": super_password + "x"}
        )
        self.assertEqual(expected, actual)

    def test_password_invalid_password(self):
        setup_account()
        self.client.init()

        expected = {"error": "permissions denied"}
        actual = self.client.request({"action": "password", "name": "super", "password": super_password, "new": "x"})
        self.assertEqual(expected, actual)

    def test_password_successful(self):
        setup_account()
        self.client.init()

        expected = {"success": True}
        actual = self.client.request(
            {"action": "password", "name": "super", "password": super_password, "new": super_password + "x"}
        )
        self.assertEqual(expected, actual)

        with self.assertRaises(InvalidLoginException):
            self.client.login("super", super_password)

        self.assertTrue(is_uuid(self.client.login("super", super_password + "x")))

    def test_settings_not_logged_in(self):
        clear_users()
        self.client.init()

        expected = {"error": "unknown action"}
        actual = self.client.request({"action": "setting", "key": "foo", "value": "bar"})
        self.assertEqual(expected, actual)

    def test_settings_add_too_long(self):
        setup_account()
        self.client.login("super", super_password)

        expected = {"error": "unsupported parameter size"}
        actual = self.client.request({"action": "setting", "key": "foo", "value": "A" * 2048})
        self.assertEqual(expected, actual)

    def test_settings_add_successful(self):
        setup_account()
        self.client.login("super", super_password)

        expected = {"key": "foo", "value": "bar"}
        actual = self.client.request({"action": "setting", "key": "foo", "value": "bar"})
        self.assertEqual(expected, actual)

    def test_settings_get_not_found(self):
        setup_account()
        execute("TRUNCATE user_settings")
        self.client.login("super", super_password)

        expected = {"error": "unknown setting"}
        actual = self.client.request({"action": "setting", "key": "foo"})
        self.assertEqual(expected, actual)

    def test_settings_get_successful(self):
        setup_account()
        execute("TRUNCATE user_settings")
        execute("INSERT INTO user_settings (user, settingKey, settingValue) VALUES (%s, 'foo', 'bar')", super_uuid)
        self.client.login("super", super_password)

        expected = {"key": "foo", "value": "bar"}
        actual = self.client.request({"action": "setting", "key": "foo"})
        self.assertEqual(expected, actual)

    def test_settings_delete_not_found(self):
        setup_account()
        execute("TRUNCATE user_settings")
        self.client.login("super", super_password)

        expected = {"error": "unknown setting"}
        actual = self.client.request({"action": "setting", "key": "foo", "delete": ""})
        self.assertEqual(expected, actual)

    def test_settings_delete_successful(self):
        setup_account()
        execute("TRUNCATE user_settings")
        execute("INSERT INTO user_settings (user, settingKey, settingValue) VALUES (%s, 'foo', 'bar')", super_uuid)
        self.client.login("super", super_password)

        expected = {"success": True}
        actual = self.client.request({"action": "setting", "key": "foo", "delete": ""})
        self.assertEqual(expected, actual)

    def test_ms_endpoint_not_found(self):
        setup_account()
        self.client.login("super", super_password)

        tag = uuid()
        expected = {"error": "missing action"}
        actual = self.client.request({"tag": tag, "ms": "doesntexist", "endpoint": ["test"], "data": {}})
        self.assertEqual(expected, actual)
