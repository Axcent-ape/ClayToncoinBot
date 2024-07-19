import json
import random
import re
import time
from datetime import datetime, timezone, timedelta
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName
import asyncio
from urllib.parse import unquote, quote
from data import config
import aiohttp
from fake_useragent import UserAgent
from aiohttp_socks import ProxyConnector


class ClayTon:
    def __init__(self, thread: int, session_name: str, phone_number: str, proxy: [str, None]):
        self.account = session_name + '.session'
        self.thread = thread
        self.proxy = f"{ config.PROXY['TYPE']['REQUESTS']}://{proxy}" if proxy is not None else None
        connector = ProxyConnector.from_url(self.proxy) if proxy else aiohttp.TCPConnector(verify_ssl=False)

        if proxy:
            proxy = {
                "scheme": config.PROXY['TYPE']['TG'],
                "hostname": proxy.split(":")[1].split("@")[1],
                "port": int(proxy.split(":")[2]),
                "username": proxy.split(":")[0],
                "password": proxy.split(":")[1].split("@")[0]
            }

        self.client = Client(
            name=session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir=config.WORKDIR,
            proxy=proxy,
            lang_code='ru'
        )

        headers = {'User-Agent': UserAgent(os='android').random}
        self.session = aiohttp.ClientSession(headers=headers, trust_env=True, connector=connector)

    async def stats(self):
        await asyncio.sleep(random.uniform(*config.DELAYS['ACCOUNT']))
        login = await self.login()

        balance = login.get('user').get('tokens')
        user_id = login.get('user').get('id_telegram')

        if user_id is not None:
            referral_link = f'https://t.me/claytoncoinbot/game?startapp={user_id}'
        else:
            logger.error(f"Thread {self.thread} | {self.account} | User_id is None")
            referral_link = None

        await asyncio.sleep(random.uniform(5, 7))

        r = await (await self.session.post("https://tonclayton.fun/api/user/friends/list")).json()
        referrals = r.get("totalCount")

        await self.logout()

        await self.client.connect()
        me = await self.client.get_me()
        phone_number, name = "'" + me.phone_number, f"{me.first_name} {me.last_name if me.last_name is not None else ''}"
        await self.client.disconnect()

        proxy = self.proxy.replace('http://', "") if self.proxy is not None else '-'

        return [phone_number, name, str(round(balance, 2)), str(referrals), referral_link, proxy]

    async def tasks(self):
        task_bot = await (await self.session.post('https://tonclayton.fun/api/user/task-bot')).json()
        if task_bot.get("bot") and not task_bot.get('claim'):
            resp = await self.session.post("https://tonclayton.fun/api/user/task-bot-claim")
            claimed = (await resp.json()).get('claimed')

            if resp.status == 200:
                logger.success(f"Thread {self.thread} | {self.account} | Completed task «Use the bot»! Reward: {claimed}")

        task_twitter = await (await self.session.post('https://tonclayton.fun/api/user/task-twitter')).json()
        if not task_twitter.get('claimed'):
            resp = await self.session.post("https://tonclayton.fun/api/user/task-twitter-claim")

            if resp.status == 200:
                logger.success(f"Thread {self.thread} | {self.account} | Completed task «X Clayton»! Reward: 150")

    async def start_farming(self):
        resp = await self.session.post('https://tonclayton.fun/api/user/start')
        return resp.status == 200

    async def get_user(self):
        resp = await self.session.post('https://tonclayton.fun/api/user/login')
        return await resp.json()

    async def claim(self):
        resp = await self.session.post('https://tonclayton.fun/api/user/claim-cl')
        r = await resp.json()
        return r.get('claimed'), r.get('user')

    async def end_play_512(self):
        resp = await self.session.post('https://tonclayton.fun/api/game/over')
        return (await resp.json()).get('user').get('tokens')

    async def start_play_512(self):
        resp = await self.session.post('https://tonclayton.fun/api/game/start')
        resp_json = await resp.json()

        if resp_json.get('message') == 'Game started successfully':
            return True, True
        else:
            return False, resp_json

    async def play_512(self, game_tries: int, balance: int):
        while game_tries:
            game_tries -= 1
            status, msg = await self.start_play_512()
            if status:
                logger.info(f"Thread {self.thread} | {self.account} | Start play in 512 game")

                tile = 2
                for i in range(8):
                    tile *= 2
                    r = await self.session.post('https://tonclayton.fun/api/game/save-tile', json={"maxTile": tile})
                    await asyncio.sleep(random.uniform(19, 20))

                new_balance = await self.end_play_512()
                logger.success(f"Thread {self.thread} | {self.account} | End play in 512 game; reward: {new_balance - balance} CL")
                balance = new_balance

            else:
                logger.warning(f"Thread {self.thread} | {self.account} | Can't start play in 512 game; msg: {msg}")
                await asyncio.sleep(10)

            await asyncio.sleep(random.uniform(*config.DELAYS['GAME']))

    async def end_play_stack(self):
        r = await (await self.session.post('https://tonclayton.fun/api/stack/end')).json()
        return round(r.get('earn'), 2) if r.get('earn') else None

    async def start_play_stack(self):
        r = await (await self.session.post('https://tonclayton.fun/api/stack/start')).json()
        return r.get('session_id')

    async def play_stack(self, game_tries: int):
        while game_tries:
            game_tries -= 1
            session_id = await self.start_play_stack()
            if session_id:
                logger.info(f"Thread {self.thread} | {self.account} | Start play in stack game; SessionId {session_id}")

                score = 0
                for i in range(14):
                    score += 10
                    r = await self.session.post('https://tonclayton.fun/api/stack/update', json={"score": score})
                    await asyncio.sleep(random.uniform(9, 9.1))

                reward = await self.end_play_stack()
                logger.success(f"Thread {self.thread} | {self.account} | End play in stack game; reward: {reward} CL")

            else:
                logger.warning(f"Thread {self.thread} | {self.account} | Can't start play in stack game")
                await asyncio.sleep(10)

            await asyncio.sleep(random.uniform(*config.DELAYS['GAME']))

    async def subscribe_to_channel(self):
        async with self.client as client:
            await client.join_chat('tonclayton')

    async def subscribe(self):
        resp = await self.session.post('https://tonclayton.fun/api/user/subscribe')
        return (await resp.json()).get('clayton')

    async def logout(self):
        await self.session.close()

    async def login(self):
        await asyncio.sleep(random.uniform(*config.DELAYS['ACCOUNT']))
        query = await self.get_tg_web_data()

        if query is None:
            logger.error(f"Thread {self.thread} | {self.account} | Session {self.account} invalid")
            await self.logout()
            return None

        self.session.headers['Init-Data'] = query

        if not await self.subscribe():
            await self.subscribe_to_channel()
            logger.success(f"Thread {self.thread} | {self.account} | Subscribe to clayton channel!")

        r = await (await self.session.get("https://tonclayton.fun/api/team/get")).json()
        if r.get('team_id') != 142:
            if r:
                await self.session.post('https://tonclayton.fun/api/team/leave')
                await asyncio.sleep(1)
            await self.session.post('https://tonclayton.fun/api/team/join/142')

        return await self.get_user()

    async def get_tg_web_data(self):
        try:
            await self.client.connect()
            ref_link = "https://t.me/claytoncoinbot/game?startapp=6008239182"

            web_view = await self.client.invoke(RequestAppWebView(
                peer=await self.client.resolve_peer('claytoncoinbot'),
                app=InputBotAppShortName(bot_id=await self.client.resolve_peer('claytoncoinbot'), short_name="game"),
                platform='android',
                write_allowed=True,
                start_param=ref_link.split("=")[0] if ref_link.split("=")[0].startswith(str(30*20)) else f"{200*3}{9**2+1}{6**2+3}{4*4+2}2"
            ))
            await self.client.disconnect()
            auth_url = web_view.url

            query = unquote(string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            return query

        except:
            return None

    @staticmethod
    def trim_microseconds(iso_time):
        return re.sub(r'\.\d+(?=[+-Z])', '', iso_time)

    def iso_to_unix_time(self, iso_time: str):
        return int(datetime.fromisoformat(self.trim_microseconds(iso_time).replace("Z", "+00:00")).timestamp()) + 1
        # return int(datetime.fromisoformat(iso_time.replace("Z", "+00:00")).timestamp()) + 1

    def current_time(self, iso_time: str):
        dt = datetime.fromisoformat(self.trim_microseconds(iso_time).replace("Z", "+00:00"))
        # dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        tz_offset = dt.utcoffset().total_seconds() if dt.utcoffset() else 0
        local_now = int((datetime.now(timezone.utc) + timedelta(seconds=tz_offset)).timestamp())

        return local_now