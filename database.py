from pymysql import connect, Connection

db: Connection = connect(host="172.18.0.2", user="cryptic", password="cryptic", db="cryptic", charset="utf8mb4")


def query(sql, *args) -> dict:
    with db.cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def execute(sql, *args):
    with db.cursor() as cursor:
        cursor.execute(sql, args)
    db.commit()
