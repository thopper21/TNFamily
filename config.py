# config.py
import os
from urllib.parse import quote_plus


def parse_approved_emails(value: str) -> list:
    return [e.strip() for e in value.split(',') if e.strip()]


def _build_cloud_db_url():
    user = os.environ.get('DB_USER', '')
    password = quote_plus(os.environ.get('DB_PASSWORD', ''))
    name = os.environ.get('DB_NAME', '')
    instance = os.environ.get('CLOUD_SQL_CONNECTION_NAME', '')
    if user and name and instance:
        return f"postgresql+psycopg2://{user}:{password}@/{name}?host=/cloudsql/{instance}"
    return os.environ.get('DATABASE_URL')


class Config:
    APP_NAME = os.environ.get('APP_NAME', 'Family Hub')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    APPROVED_EMAILS = parse_approved_emails(os.environ.get('APPROVED_EMAILS', ''))
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class LocalConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tnfamily.db'


class CloudConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _build_cloud_db_url()
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 2,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }


config_map = {
    'local': LocalConfig,
    'cloud': CloudConfig,
}
