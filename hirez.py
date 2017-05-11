import asyncio
import collections
import datetime
import hashlib
import json

import aiohttp

ENDPOINTS = {
    'smite-pc': 'http://api.smitegame.com/smiteapi.svc',
    'smite-xbl': '',
    'smite-psn': '',
    'paladins-pc': '',
}


HirezSession = collections.namedtuple('HirezSession', 'id timestamp')


class HirezAPI:
    def __init__(self, endpoint: str, dev_id: str, auth_key: str, loop: asyncio.AbstractEventLoop = None,
                 sess: aiohttp.ClientSession = None):
        self.endpoint = ENDPOINTS[endpoint]
        self.dev_id = dev_id
        self.auth_key = auth_key
        self.loop = loop or asyncio.get_event_loop()
        self.sess = sess or aiohttp.ClientSession(loop=self.loop)
        self.hirez_session = None
        self.auth_lock = asyncio.Lock(loop=self.loop)

    async def auth(self):
        async with self.auth_lock:
            now = datetime.datetime.utcnow()
            if self.hirez_session is None or self.hirez_session.timestamp < now - datetime.timedelta(minutes=15):
                # Refresh session
                result = await self._make_request('createsession', with_session=False)
                if result['ret_msg'] == 'Approved':
                    self.hirez_session = HirezSession(result['session_id'], now)
                    return result
                else:
                    raise Exception('Failed to create session: {}'.format(result['ret_msg']))

    async def test_session(self):
        print(await self.auth())
        return await self._make_request('testsession')

    async def data_used(self):
        print(await self.auth())
        return await self._make_request('getdataused')

    async def player(self, player_id):
        print(await self.auth())
        return await self._make_request('getplayer', player_id)

    async def team(self, team_id):
        print(await self.auth())
        return await self._make_request('getteamdetails', team_id)

    async def team_players(self, team_id):
        print(await self.auth())
        return await self._make_request('getteamplayers', team_id)

    async def player_status(self, player_id):
        print(await self.auth())
        return await self._make_request('getplayerstatus', player_id)

    async def _make_request(self, method: str, *args, with_session=True):
        timestamp = datetime.datetime.utcnow()
        sig = self._signature(method, timestamp)
        args = '/'.join(str(arg) for arg in args)
        args = '/{}'.format(args) if args else ''
        session = '/{}'.format(self.hirez_session.id) if with_session else ''
        url = '{0.endpoint}/{1}Json/{0.dev_id}/{2}{3}/{4:%Y%m%d%H%M%S}{5}'.format(
            self, method, sig, session, timestamp, args
        )
        async with self.sess.get(url) as resp:
            print(resp.url)
            print(resp.status)
            result = json.loads(await resp.text())
        return result

    def _signature(self, method: str, timestamp: datetime.datetime):
        sig_str = '{0.dev_id}{1}{0.auth_key}{2:%Y%m%d%H%M%S}'.format(self, method, timestamp)
        return hashlib.md5(sig_str.encode()).hexdigest()
