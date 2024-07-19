import os
import random

from utils.clayton import ClayTon
from aiohttp.client_exceptions import ContentTypeError
from data import config
from utils.core import logger
import datetime
import pandas as pd
from utils.core.telegram import Accounts
import asyncio


async def start(thread: int, session_name: str, phone_number: str, proxy: [str, None]):
    clay = ClayTon(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy)
    account = session_name + '.session'

    await clay.login()
    while True:
        try:
            await clay.tasks()

            login = await clay.get_user()
            user = login['user']
            game_tries, balance, start_time = user['daily_attempts'], user['tokens'], user['start_time']

            # await clay.play_512(game_tries, balance)
            await clay.play_stack(game_tries)

            if clay.iso_to_unix_time(start_time)+32400 > clay.current_time(start_time):
                sleep = clay.iso_to_unix_time(start_time)+32400 - clay.current_time(start_time)
                logger.info(f"Thread {thread} | {account} | Wait {sleep} seconds for a new play tries")
                await asyncio.sleep(sleep)

            user = await clay.get_user()
            start_time = user['user']['start_time']

            if clay.iso_to_unix_time(start_time)+32400 < clay.current_time(start_time) and user['user']['active_farm']:
                claimed, u = await clay.claim()
                if claimed:
                    logger.success(f"Thread {thread} | {account} | Claimed {round(claimed, 2)} points; Balance: {u['tokens']}")

            if clay.iso_to_unix_time(start_time)+32400 < clay.current_time(start_time) and not user['user']['active_farm']:
                if await clay.start_farming():
                    logger.success(f"Thread {thread} | {account} | Start farming")

            await asyncio.sleep(random.uniform(*config.DELAYS['REPEAT']))

        except ContentTypeError as e:
            logger.error(f"Thread {thread} | {account} | Error: {e}")
            await asyncio.sleep(120)

        except Exception as e:
            logger.error(f"Thread {thread} | {account} | Error: {e}")
            await asyncio.sleep(5)

    await clay.logout()


async def stats():
    accounts = await Accounts().get_accounts()

    tasks = []
    for thread, account in enumerate(accounts):
        session_name, phone_number, proxy = account.values()
        tasks.append(asyncio.create_task(ClayTon(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy).stats()))

    data = await asyncio.gather(*tasks)

    path = f"statistics/statistics_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"
    columns = ['Phone number', 'Name', 'Balance', 'Referrals', 'Referral link', 'Proxy (login:password@ip:port)']

    if not os.path.exists('statistics'): os.mkdir('statistics')
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(path, index=False, encoding='utf-8-sig')

    logger.success(f"Saved statistics to {path}")
