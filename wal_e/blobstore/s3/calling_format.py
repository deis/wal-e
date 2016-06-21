import os
import urlparse

import boto3
import botocore
from botocore.utils import fix_s3_host

from wal_e import log_help
from wal_e.exception import UserException

logger = log_help.WalELogger(__name__)


def _s3connection_opts_from_uri(impl):
    # 'impl' should look like:
    #
    #    <protocol>://[user:pass]@<host>[:port]
    #
    # A concrete example:
    #
    #     https://user:pass@localhost:1235
    o = urlparse.urlparse(impl, allow_fragments=False)

    if o.scheme is not None:
        if o.scheme not in ['http', 'https']:
            raise UserException(
                msg='WALE_S3_ENDPOINT URI scheme is invalid',
                detail='The scheme defined is ' + repr(o.scheme),
                hint='An example of a valid scheme is https.')

    if o.username is not None or o.password is not None:
        raise UserException(
            msg='WALE_S3_ENDPOINT does not support username or password')

    if o.path:
        raise UserException(
            msg='WALE_S3_ENDPOINT does not support a URI path',
            detail='Path is {0!r}'.format(o.path))

    if o.query:
        raise UserException(
            msg='WALE_S3_ENDPOINT does not support query parameters')

    config = botocore.client.Config(signature_version='s3v4')

    return {'endpoint_url': impl, 'config': config}


def _is_ipv4_like(s):
    """Find if a string superficially looks like an IPv4 address.

    AWS documentation plays it fast and loose with this; in other
    regions, it seems like even non-valid IPv4 addresses (in
    particular, ones that possess decimal numbers out of range for
    IPv4) are rejected.
    """
    parts = s.split('.')

    if len(parts) != 4:
        return False

    for part in parts:
        try:
            int(part)
        except ValueError:
            return False

    return True


def _is_mostly_subdomain_compatible(bucket_name):
    """Returns True if SubdomainCallingFormat can be used...mostly

    This checks to make sure that putting aside certificate validation
    issues that a bucket_name is able to use the
    SubdomainCallingFormat.
    """
    return (bucket_name.lower() == bucket_name and
            len(bucket_name) >= 3 and
            len(bucket_name) <= 63 and
            '_' not in bucket_name and
            '..' not in bucket_name and
            '-.' not in bucket_name and
            '.-' not in bucket_name and
            not bucket_name.startswith('-') and
            not bucket_name.endswith('-') and
            not bucket_name.startswith('.') and
            not bucket_name.endswith('.') and
            not _is_ipv4_like(bucket_name))


class CallingInfo(object):
    """Encapsulate information used to produce a S3Connection."""

    def __str__(self):
        return repr(self)

    def connect(self, creds):
        """
        Return a boto S3 client set up with great care... Unless the
        user provides WALE_S3_ENDPOINT, in which case we interpret
        the URI and assume they know what they're doing.
        """
        # If WALE_S3_ENDPOINT is set, do not attempt to guess
        # the right calling conventions and instead honor the explicit
        # settings within WALE_S3_ENDPOINT.
        impl = os.getenv('WALE_S3_ENDPOINT')
        if impl:
            logger.info(
                'connecting to S3 with WALE_S3_ENDPOINT ({})'.format(impl))
            conn = boto3.resource('s3', **_s3connection_opts_from_uri(impl))
            conn.meta.client.meta.events.unregister(
                'before-sign.s3',
                fix_s3_host)
        else:
            logger.info('connecting to S3 with creds ({})'.format(creds))
            # connect using the safest available options.
            conn = boto3.resource('s3')
        # Remove the handler that switches S3 requests to virtual host style
        # addressing.
        return conn
