import pytest

from wal_e import exception
from wal_e.blobstore.s3 import calling_format


def test_bad_proto():
    with pytest.raises(exception.UserException):
        calling_format._s3connection_opts_from_uri('nope://')


def test_port():
    opts = calling_format._s3connection_opts_from_uri(
        'https://localhost:443')
    assert ':443' in opts['endpoint_url']


def test_reject_auth():
    for username in ['', 'hello']:
        for password in ['', 'world']:
            with pytest.raises(exception.UserException):
                calling_format._s3connection_opts_from_uri(
                    'https://{0}:{1}@localhost:443'
                    .format(username, password))


def test_reject_path():
    with pytest.raises(exception.UserException):
        calling_format._s3connection_opts_from_uri(
            'https://localhost/hello')


def test_reject_query():
    with pytest.raises(exception.UserException):
        calling_format._s3connection_opts_from_uri(
            'https://localhost?q=world')


def test_reject_fragment():
    with pytest.raises(exception.UserException):
        print calling_format._s3connection_opts_from_uri(
            'https://localhost#hello')
