import json
import sys

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from aliyunpan.api.utils import logger
from aliyunpan.common import *
from aliyunpan.exceptions import AliyunpanCode, InvalidAccessToken, InvalidRefreshToken, LoginFailed

__all__ = ['Req']

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Req:
    def __init__(self, disk=None):
        self._disk = disk
        self._retry_num = 3
        self._session = requests.Session()
        self._timeout = 5
        self._verify = False
        self._host_url = 'https://www.aliyundrive.com/'
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Referer': self._host_url,
        }

    def _req(self, method, *args, **kwargs):
        try:
            kwargs.setdefault('timeout', self._timeout)
            kwargs.setdefault('verify', self._verify)
            kwargs.setdefault('stream', False)
            stream = kwargs['stream']
            kwargs.setdefault('depth', self._retry_num)
            depth = kwargs.pop('depth')
            kwargs['headers'] = kwargs['headers'] if 'headers' in kwargs else {}
            kwargs['headers'].update(self._headers)
            if 'access_token' in kwargs:
                if kwargs['access_token']:
                    kwargs['headers']['Authorization'] = kwargs['access_token']
                else:
                    kwargs['headers']['Authorization'] = None
                del kwargs['access_token']
            else:
                kwargs['headers']['Authorization'] = self._disk.access_token if self._disk else GLOBAL_VAR.access_token
            r = getattr(self._session, method.lower())(*args, **kwargs)
            try:
                logger.debug(r.status_code)
                if depth:
                    if self._disk and not stream and json.loads(r.text)['code'] == AliyunpanCode.token_invalid:
                        depth -= 1
                        try:
                            self._disk.access_token = self._disk.get_access_token()
                        except InvalidRefreshToken:
                            self._disk.login()
                        return self._req(method, depth=depth, *args, **kwargs)
                else:
                    raise InvalidAccessToken
            except (KeyboardInterrupt, InvalidAccessToken, LoginFailed):
                raise
            except json.decoder.JSONDecodeError:
                logger.debug(r.text)
            except KeyError:
                pass
            except:
                logger.debug(sys.exc_info())
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
