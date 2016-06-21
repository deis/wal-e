from wal_e.blobstore.s3 import calling_format
from wal_e.blobstore.s3.calling_format import (
    _is_mostly_subdomain_compatible,
    _is_ipv4_like,
)

SUBDOMAIN_BOGUS = [
    '1.2.3.4',
    'myawsbucket.',
    'myawsbucket-.',
    'my.-awsbucket',
    '.myawsbucket',
    'myawsbucket-',
    '-myawsbucket',
    'my_awsbucket',
    'my..examplebucket',

    # Too short.
    'sh',

    # Too long.
    'long' * 30,
]

SUBDOMAIN_OK = [
    'myawsbucket',
    'my-aws-bucket',
    'myawsbucket.1',
    'my.aws.bucket'
]


def test_subdomain_detect():
    """Exercise subdomain compatible/incompatible bucket names."""
    for bn in SUBDOMAIN_OK:
        assert _is_mostly_subdomain_compatible(bn) is True

    for bn in SUBDOMAIN_BOGUS:
        assert _is_mostly_subdomain_compatible(bn) is False


def test_ipv4_detect():
    """IPv4 lookalikes are not valid SubdomainCallingFormat names

    Even though they otherwise follow the bucket naming rules,
    IPv4-alike names are called out as specifically banned.
    """
    assert _is_ipv4_like('1.1.1.1') is True

    # Out-of IPv4 numerical range is irrelevant to the rules.
    assert _is_ipv4_like('1.1.1.256') is True
    assert _is_ipv4_like('-1.1.1.1') is True

    assert _is_ipv4_like('1.1.1.hello') is False
    assert _is_ipv4_like('hello') is False
    assert _is_ipv4_like('-1.1.1') is False
    assert _is_ipv4_like('-1.1.1.') is False


def test_str_repr_call_info():
    """Ensure CallingInfo renders sensibly."""
    cinfo = calling_format.CallingInfo()
    assert repr(cinfo) == str(cinfo)
