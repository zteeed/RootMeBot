from typing import Any, Dict, Optional
from dotenv import load_dotenv

import aiohttp
import aiohttp.client_exceptions
import aiohttp.client_reqrep
from os import environ
import sys

from bot.colors import green, red
from bot.constants import URL, timeout

load_dotenv()
response_content_type = Optional[Dict[str, Any]]

ROOTME_ACCOUNT_LOGIN = environ.get('ROOTME_ACCOUNT_LOGIN')
ROOTME_ACCOUNT_PASSWORD = environ.get('ROOTME_ACCOUNT_PASSWORD')
cookies = {}


async def get_cookies():
    async with aiohttp.ClientSession() as session:
        data = dict(login=ROOTME_ACCOUNT_LOGIN, password=ROOTME_ACCOUNT_PASSWORD)
        async with session.post(f'{URL}/login', data=data, timeout=timeout) as response:
            if response.status == 200:
                content = await response.json(content_type=None)
                return dict(spip_session=content[0]['info']['spip_session'])
            red('Wrong credentials.')
            sys.exit(0)


async def request_to(url: str) -> response_content_type:
    global cookies
    async with aiohttp.ClientSession() as session:
        async with session.get(url, cookies=cookies, timeout=timeout) as response:
            if response.url.host not in URL:  # website page is returned not API (api.www.root-me.org / www.root-me.org)
                return None
            if response.status == 200:
                print(await response.json())
                return await response.json()
            elif response.status == 401:
                cookies = await get_cookies()
                await request_to(url)
            else:
                return None


async def extract_json(url: str) -> response_content_type:
    data = await request_to(url)
    print(data)
    if data is None:
        red(url)
    else:
        green(url)
        if 'body' in data.keys():
            data = data['body']
    return data


class Parser:

    @staticmethod
    async def extract_default(lang: str) -> response_content_type:
        return await extract_json(f'{URL}/{lang}')

    @staticmethod
    async def extract_rootme_profile(user: str, lang: str) -> response_content_type:
        return await extract_json(f'{URL}/{lang}/{user}/profile')

    @staticmethod
    async def extract_rootme_details(user: str, lang: str) -> response_content_type:
        return await extract_json(f'{URL}/{lang}/{user}/details')

    @staticmethod
    async def extract_rootme_stats(user: str, lang: str) -> response_content_type:
        return await extract_json(f'{URL}/{lang}/{user}/stats')

    @staticmethod
    async def extract_score(user: str, lang: str) -> int:
        rootme_profile = await Parser.extract_rootme_profile(user, lang)
        return rootme_profile[0]['score']

    @staticmethod
    async def extract_categories(lang: str) -> response_content_type:
        return await extract_json(f'{URL}/challenges?lang={lang}')
