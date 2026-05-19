# config.py
import os


def parse_approved_emails(value: str) -> list:
    return [e.strip() for e in value.split(',') if e.strip()]


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
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config_map = {
    'local': LocalConfig,
    'cloud': CloudConfig,
}
