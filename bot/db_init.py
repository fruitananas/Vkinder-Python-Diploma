from sqlalchemy.engine import create_engine
from sqlalchemy import MetaData, Table, String, Column, Boolean, Integer
from dotenv import load_dotenv
import os


load_dotenv()

metadata = MetaData()

found_users = Table('found_users', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(20), unique=True, index=True),
    Column('first_name', String(40)),
    Column('last_name', String(40)),
    Column('age', Integer),
    Column('city', Integer),
    Column('sex', Integer),
    Column('user_url', String(50)),
    Column('seen', Boolean, default=False)
)

user_preferences = Table('user_preferences', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(20), unique=True),
    Column('age_from', Integer),
    Column('age_to', Integer),
    Column('city', Integer),
    Column('sex', Integer)
)


def init_db():
    user = os.environ.get('POSTGRES_USER')
    passwd = os.environ.get('POSTGRES_PASSWD')
    db_name = os.environ.get('DB_NAME')
    engine = create_engine(f'postgresql+psycopg2://{user}:{passwd}@localhost/{db_name}')
    metadata.create_all(engine)
    return engine
