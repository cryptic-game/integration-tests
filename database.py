from pymysql import connect, Connection

from environment import DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_DATABASE

db: Connection = connect(
    host=DB_HOST, port=DB_PORT, user=DB_USERNAME, password=DB_PASSWORD, db=DB_DATABASE, charset="utf8mb4"
)


def query(sql, *args) -> dict:
    with db.cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def execute(sql, *args):
    with db.cursor() as cursor:
        cursor.execute(sql, args)
    db.commit()
