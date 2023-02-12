from sqlalchemy.engine import create_engine
from sqlalchemy import MetaData, Table, String, Column, Integer
from dotenv import load_dotenv
import os


load_dotenv()

metadata = MetaData()


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
