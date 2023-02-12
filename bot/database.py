from sqlalchemy.sql.expression import select, insert, delete

from .db_init import init_db, user_preferences


class DBInstance:
    def __init__(self):
        self.engine = init_db()
        self.conn = self.engine.connect()

    def is_registered(self, user_id):
        user_id = str(user_id)
        query = select(user_preferences).\
                where(user_preferences.c.user_id == user_id)
        result = self.conn.execute(query)
        return len(result.fetchall()) > 0

    def register_user(self, user_id, age_from, age_to, city, sex):
        user_id = str(user_id)
        if self.is_registered(user_id):
            subquery = delete(user_preferences).\
                       where(user_preferences.c.user_id == user_id)
            self.conn.execute(subquery)
        query = insert(user_preferences).values(
            user_id=user_id,
            age_from=age_from,
            age_to=age_to,
            city=city,
            sex=sex
        )
        self.conn.execute(query)

    def search_preferences(self, user_id):
        user_id = str(user_id)
        query = select(user_preferences.c.age_from, user_preferences.c.age_to,
                       user_preferences.c.city, user_preferences.c.sex).\
                where(user_preferences.c.user_id == user_id)
        result = self.conn.execute(query)
        return result.fetchone()
