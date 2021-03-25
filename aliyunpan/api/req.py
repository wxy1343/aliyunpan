import asyncio
import functools

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from aliyunpan.api.utils import *

__all__ = ['Req']
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Req:
    def __init__(self):
        self._session = requests.Session()
        self._timeout = 5
        self._verify = False
        self._host_url = 'https://www.aliyundrive.com'
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Referer': 'https://www.aliyundrive.com/',
        }

    def _req(self, method, *args, **kwargs):
        try:
            kwargs.setdefault('timeout', self._timeout)
            kwargs.setdefault('verify', self._verify)
            if 'headers' in kwargs:
                kwargs['headers'].update(self._headers)
            else:
                kwargs['headers'] = self._headers
            r = getattr(self._session, method)(*args, **kwargs)
            logger.debug(r.status_code)
            return r
        except requests.exceptions.RequestException:
            raise

    async def _req_async(self, method, *args, **kwargs):
        try:
            kwargs.setdefault('timeout', self._timeout)
            kwargs.setdefault('verify', self._verify)
            kwargs.setdefault('async_timeout', None)
            async_timeout = kwargs['async_timeout']
            kwargs.pop('async_timeout')
            if 'headers' in kwargs:
                kwargs['headers'].update(self._headers)
            else:
                kwargs['headers'] = self._headers
            return await async_run_sync(functools.partial(getattr(self._session, method), *args, **kwargs),
                                        async_timeout)
        except requests.exceptions.RequestException:
            raise
        except asyncio.exceptions.TimeoutError:
            raise

    async def async_run_sync(self, fun, async_timeout):
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(loop.run_in_executor(None, fun), async_timeout)

    def get(self, *args, **kwargs):
        return self._req('get', *args, **kwargs)

    async def get_async(self, *args, **kwargs):
        return await self._req_async('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._req('post', *args, **kwargs)

    async def post_async(self, *args, **kwargs):
        return await self._req_async('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._req('put', *args, **kwargs)

    async def put_async(self, *args, **kwargs):
        return await self._req_async('put', *args, **kwargs)

    def head(self, *args, **kwargs):
        return self._req('head', *args, **kwargs)

    async def head_async(self, *args, **kwargs):
        return await self._req_async('head', *args, **kwargs)

    def options(self, *args, **kwargs):
        return self._req('options', *args, **kwargs)

    async def options_async(self, *args, **kwargs):
        return await self._req_async('options', *args, **kwargs)

    def req(self, method, *args, **kwargs):
        return self._req(method, *args, **kwargs)
