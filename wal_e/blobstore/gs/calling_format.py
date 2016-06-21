from oauth2client.service_account import ServiceAccountCredentials
from gcloud.storage.connection import Connection
from gcloud.storage.client import Client
from gevent.local import local
from httplib2 import Http

import json


class CallingInfo(object):
    """Encapsulate information used to produce a GCS Connection."""

    def __str__(self):
        return repr(self)

    def connect(self, creds):
        scopes = ['https://www.googleapis.com/auth/devstorage.full_control']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            creds.service_account, scopes=scopes)
        with open(creds.service_account) as data_file:
            data = json.load(data_file)
        client = Client(credentials=credentials, project=data['project_id'],
                http=ThreadSafeHttp(credentials))
        return client


class ThreadSafeHttp(object):

    __scoped_credentials = None
    __local = local()

    def __init__(self, creds):
        self.__scoped_credentials = Connection._create_scoped_credentials(
            creds, Connection.SCOPE)

    def __getattr__(self, name):
        if not hasattr(self.__local, 'http'):
            self.__local.http = self.__scoped_credentials.authorize(Http())

        return getattr(self.__local.http, name)
