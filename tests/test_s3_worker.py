import os

import botocore
import pytest

from s3_integration_help import (
    FreshBucket,
    no_real_s3_credentials,
)

from wal_e import storage
from wal_e.blobstore.s3 import Credentials
from wal_e.blobstore.s3 import do_lzop_get
from wal_e.worker.s3 import BackupList

# Contrivance to quiet down pyflakes, since pytest does some
# string-evaluation magic in test collection.
no_real_s3_credentials = no_real_s3_credentials


@pytest.mark.skipif("no_real_s3_credentials()")
def test_301_redirect():
    """Integration test for bucket naming issues this test."""

    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    bucket_name = 'wal-e-test-301-redirect' + aws_access_key.lower()

    with pytest.raises(botocore.exceptions.ClientError) as e:
        # Just initiating the bucket manipulation API calls is enough
        # to provoke a 301 redirect.
        with FreshBucket(bucket_name) as fb:
            fb.create()

    assert int(e.response['Error']['Code']) == 301


@pytest.mark.skipif("no_real_s3_credentials()")
def test_get_bucket_vs_certs():
    """Integration test for bucket naming issues."""
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')

    # Add dots to try to trip up TLS certificate validation.
    bucket_name = 'wal-e.test.dots.' + aws_access_key.lower()

    with pytest.raises(botocore.exceptions.ClientError) as e:
        with FreshBucket(bucket_name):
            pass

    assert e.response['Error']['Foo'] == 'bar'
    assert int(e.response['Error']['Code']) == 400


@pytest.mark.skipif("no_real_s3_credentials()")
def test_empty_latest_listing():
    """Test listing a 'backup-list LATEST' on an empty prefix."""

    bucket_name = 'wal-e-test-empty-listing'
    layout = storage.StorageLayout('s3://{0}/test-prefix'
                                   .format(bucket_name))

    with FreshBucket(bucket_name,
                     endpoint_url='http://s3.amazonaws.com') as fb:
        fb.create()
        bl = BackupList(fb.conn, layout, False)
        found = list(bl.find_all('LATEST'))
        assert len(found) == 0


@pytest.mark.skipif("no_real_s3_credentials()")
def test_404_termination(tmpdir):
    bucket_name = 'wal-e-test-404-termination'
    creds = Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                        os.getenv('AWS_SECRET_ACCESS_KEY'))

    with FreshBucket(bucket_name,
                     endpoint_url='http://s3.amazonaws.com') as fb:
        fb.create()

        target = unicode(tmpdir.join('target'))
        ret = do_lzop_get(creds, 's3://' + bucket_name + '/not-exist.lzo',
                          target, False)
        assert ret is False
