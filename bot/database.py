from sqlalchemy.sql.expression import select, insert, delete, update

from .db_init import init_db, found_users, user_preferences


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

    def get_users_by_criteria(self, age_from, age_to, city, sex):
        query = select(found_users.c.user_id, found_users.c.user_url,
                       found_users.c.first_name, found_users.c.last_name,
                       found_users.c.city, found_users.c.age).\
                where(found_users.c.city == city).\
                where(found_users.c.sex == sex).\
                where(found_users.c.seen == False).\
                where(found_users.c.age.between(age_from, age_to)).\
                limit(3)
        data = self.conn.execute(query)
        return data.fetchall()

    def user_in_database(self, user_id):
        query = select(found_users).\
                where(found_users.c.user_id == user_id)
        result = self.conn.execute(query)
        return len(result.fetchall()) > 0

    def insert_searched_user(self, item):
        if self.user_in_database(str(item['user_id'])):
            return
        query = insert(found_users).\
                values(
                    user_id=str(item['user_id']),
                    first_name=item['first_name'],
                    last_name=item['last_name'],
                    age=item['age'],
                    city=item['city'],
                    sex=item['sex'],
                    user_url=item['user_url'],
                    seen=item['seen']
                )
        self.conn.execute(query)

    def update_seen_users(self, users_ids):
        users_ids = tuple(map(str, users_ids))
        query = update(found_users).\
                where(found_users.c.user_id.in_(users_ids)).\
                values(seen=True)
        self.conn.execute(query)
