# tests/test_config.py
from config import LocalConfig, CloudConfig, config_map, parse_approved_emails


def test_local_config_debug_is_true():
    assert LocalConfig.DEBUG is True


def test_local_config_uses_sqlite():
    assert 'sqlite' in LocalConfig.SQLALCHEMY_DATABASE_URI


def test_cloud_config_debug_is_false():
    assert CloudConfig.DEBUG is False


def test_config_map_contains_local_and_cloud():
    assert 'local' in config_map
    assert 'cloud' in config_map


def test_config_map_local_is_local_config():
    assert config_map['local'] is LocalConfig


def test_config_map_cloud_is_cloud_config():
    assert config_map['cloud'] is CloudConfig


def test_parse_approved_emails_single():
    assert parse_approved_emails('a@b.com') == ['a@b.com']


def test_parse_approved_emails_multiple():
    assert parse_approved_emails('a@b.com,c@d.com') == ['a@b.com', 'c@d.com']


def test_parse_approved_emails_strips_whitespace():
    assert parse_approved_emails('  a@b.com  ,  c@d.com  ') == ['a@b.com', 'c@d.com']


def test_parse_approved_emails_empty_string():
    assert parse_approved_emails('') == []


def test_parse_approved_emails_ignores_blank_entries():
    assert parse_approved_emails('a@b.com,,c@d.com') == ['a@b.com', 'c@d.com']
