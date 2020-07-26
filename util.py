from uuid import uuid4

from PyCrypCli.client import Client


def get_client() -> Client:
    return Client("ws://127.0.0.1:8080")


def uuid() -> str:
    return str(uuid4())
