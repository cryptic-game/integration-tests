import re
from uuid import uuid4

from PyCrypCli.client import Client


def get_client() -> Client:
    return Client("ws://127.0.0.1:8080")


def is_uuid(inp: str) -> bool:
    return isinstance(inp, str) and bool(re.match(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$", inp))


def uuid() -> str:
    return str(uuid4())
