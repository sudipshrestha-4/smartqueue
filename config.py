import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def get_database_uri():
  if os.environ.get('DATABASE_URL'):
    database_url = os.environ['DATABASE_URL']

    if database_url.startswith('postgres://'):
        database_url = database_url.replace(
            'postgres://',
            'postgresql+psycopg2://',
            1
        )
    elif database_url.startswith('postgresql://'):
        database_url = database_url.replace(
            'postgresql://',
            'postgresql+psycopg2://',
            1
        )

    return database_url

    if os.environ.get('VERCEL'):
        return 'sqlite:////tmp/smartqueue.db'

    instance_dir = os.path.join(basedir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    return 'sqlite:///' + os.path.join(instance_dir, 'smartqueue.db')


class Config:
    """Base configuration shared by all environments."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-me')
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-SocketIO
    SOCKETIO_ASYNC_MODE = 'eventlet'


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
