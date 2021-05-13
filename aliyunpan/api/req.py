import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from aliyunpan.common import *

__all__ = ['Req']
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Req:
    def __init__(self):
        self._session = requests.Session()
        self._timeout = 5
        self._verify = False
        self.disk = None
        self._host_url = 'https://www.aliyundrive.com/'
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Referer': self._host_url,
        }

    def _req(self, method, *args, **kwargs):
        try:
            kwargs.setdefault('timeout', self._timeout)
            kwargs.setdefault('verify', self._verify)
            kwargs['headers'] = kwargs['headers'] if 'headers' in kwargs else {}
            kwargs['headers'].update(self._headers)
            if 'access_token' in kwargs:
                if kwargs['access_token']:
                    kwargs['headers']['Authorization'] = kwargs['access_token']
                else:
                    kwargs['headers']['Authorization'] = None
                del kwargs['access_token']
            else:
                kwargs['headers']['Authorization'] = self.disk.access_token if self.disk else GLOBAL_VAR.access_token
            r = getattr(self._session, method.lower())(*args, **kwargs)
            return r
        except requests.exceptions.RequestException:
            raise

    def get(self, *args, **kwargs) -> requests.models.Response:
        return self._req('get', *args, **kwargs)

    def post(self, *args, **kwargs) -> requests.models.Response:
        return self._req('post', *args, **kwargs)

    def put(self, *args, **kwargs) -> requests.models.Response:
        return self._req('put', *args, **kwargs)

    def head(self, *args, **kwargs) -> requests.models.Response:
        return self._req('head', *args, **kwargs)

    def options(self, *args, **kwargs) -> requests.models.Response:
        return self._req('options', *args, **kwargs)

    def req(self, method, *args, **kwargs) -> requests.models.Response:
        return self._req(method, *args, **kwargs)
