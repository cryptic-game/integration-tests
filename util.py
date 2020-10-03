from uuid import uuid4

from PyCrypCli.client import Client

from environment import SERVER_LOCATION


def get_client() -> Client:
    return Client(SERVER_LOCATION)


def uuid() -> str:
    return str(uuid4())
