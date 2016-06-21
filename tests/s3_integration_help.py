import json
import os

import boto3
import botocore
import pytest

from wal_e.blobstore import s3
from wal_e.blobstore.s3 import calling_format


def no_real_s3_credentials():
    """Helps skip integration tests without live credentials.

    Phrased in the negative to make it read better with 'skipif'.
    """
    if os.getenv('WALE_S3_INTEGRATION_TESTS') != 'TRUE':
        return True

    for e_var in ('AWS_ACCESS_KEY_ID',
                  'AWS_SECRET_ACCESS_KEY'):
        if os.getenv(e_var) is None:
            return True

    return False


def bucket_exists(conn, bucket_name):
    exists = True
    try:
        conn.meta.client.head_bucket(Bucket=bucket_name)
    except botocore.exceptions.ClientError as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the bucket does not exist.
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            exists = False
    return exists


def prepare_s3_default_test_bucket():
    # Check credentials are present: this procedure should not be
    # called otherwise.
    if no_real_s3_credentials():
        assert False

    bucket_name = 'waletdefwuy' + os.getenv('AWS_ACCESS_KEY_ID').lower()

    creds = s3.Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                           os.getenv('AWS_SECRET_ACCESS_KEY'))

    cinfo = calling_format.CallingInfo()
    conn = cinfo.connect(creds)

    def _clean():
        bucket = conn.Bucket(bucket_name)
        for key in bucket.objects.all():
            key.delete()

    if not bucket_exists(conn, bucket_name):
        conn.create_bucket(Bucket=bucket_name)

    # Make sure the bucket is squeaky clean!
    _clean()

    return bucket_name


@pytest.fixture(scope='session')
def default_test_bucket():
    if not no_real_s3_credentials():
        return prepare_s3_default_test_bucket()


def make_policy(bucket_name, prefix, allow_get_location=False):
    """Produces a S3 IAM text for selective access of data.

    Only a prefix can be listed, gotten, or written to when a
    credential is subject to this policy text.
    """
    bucket_arn = "arn:aws:s3:::" + bucket_name
    prefix_arn = "arn:aws:s3:::{0}/{1}/*".format(bucket_name, prefix)

    structure = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:ListBucket"],
                "Effect": "Allow",
                "Resource": [bucket_arn],
                "Condition": {"StringLike": {"s3:prefix": [prefix + '/*']}},
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject"],
                "Resource": [prefix_arn]
            }]}

    if allow_get_location:
        structure["Statement"].append(
            {"Action": ["s3:GetBucketLocation"],
             "Effect": "Allow",
             "Resource": [bucket_arn]})

    return json.dumps(structure, indent=2)


def _delete_keys(bucket, keys):
    for key in bucket.objects.all():
        if key in keys:
            key.delete()


def apathetic_bucket_delete(bucket_name, keys, *args, **kwargs):
    conn = boto3.client('s3', *args, **kwargs)

    if bucket_exists(conn, bucket_name):
        conn.delete_bucket(Bucket=bucket_name)

    return conn


def insistent_bucket_delete(conn, bucket_name, keys):
    if bucket_exists(conn, bucket_name):
        _delete_keys(conn.Bucket(bucket_name), keys)

    while True:
        try:
            conn.delete_bucket(Bucket=bucket_name)
        except botocore.exceptions.ClientError as e:
            if int(e.response['Error']['Code']) == 404:
                # Create not yet visible, but it just happened above:
                # keep trying.  Potential consistency.
                continue
            else:
                raise
        break


def insistent_bucket_create(conn, bucket_name, *args, **kwargs):
    while True:
        try:
            conn.create_bucket(Bucket=bucket_name, *args, **kwargs)
        except botocore.exceptions.ClientError as e:
            if int(e.response['Error']['Code']) == 409:
                # Conflict; bucket already created -- probably means
                # the prior delete did not process just yet.
                continue

            raise

        return conn.Bucket(bucket_name)


class FreshBucket(object):

    def __init__(self, bucket_name, keys=[], *args, **kwargs):
        self.bucket_name = bucket_name
        self.keys = keys
        self.conn_args = args
        self.conn_kwargs = kwargs
        self.created_bucket = False

    def __enter__(self):
        self.conn_kwargs.setdefault('verify', True)

        # Clean up a dangling bucket from a previous test run, if
        # necessary.
        self.conn = apathetic_bucket_delete(self.bucket_name,
                                            self.keys,
                                            *self.conn_args,
                                            **self.conn_kwargs)

        return self

    def create(self, *args, **kwargs):
        bucket = insistent_bucket_create(self.conn, self.bucket_name,
                                         *args, **kwargs)
        self.created_bucket = True

        return bucket

    def __exit__(self, typ, value, traceback):
        if not self.created_bucket:
            return False

        insistent_bucket_delete(self.conn, self.bucket_name, self.keys)

        return False
