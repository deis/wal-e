from wal_e.blobstore.s3 import calling_format
from wal_e.operator.backup import Backup


class S3Backup(Backup):
    """
    A performs S3 uploads to of PostgreSQL WAL files and clusters

    """

    def __init__(self, layout, creds, gpg_key_id):
        super(S3Backup, self).__init__(layout, creds, gpg_key_id)
        self.cinfo = calling_format.CallingInfo()
        from wal_e.worker.s3 import s3_worker
        self.worker = s3_worker
