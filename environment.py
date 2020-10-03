from os import getenv

DB_HOST = getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(getenv("DB_PORT", "3306"))
DB_USERNAME = getenv("DB_USERNAME", "cryptic")
DB_PASSWORD = getenv("DB_PASSWORD", "cryptic")
DB_DATABASE = getenv("DB_DATABASE", "cryptic")

SERVER_LOCATION = getenv("SERVER_LOCATION", "ws://127.0.0.1:8080")
