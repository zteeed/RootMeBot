import sys
from os import environ
from typing import Any, List, Dict, Optional, Union

import aiohttp
import aiohttp.client_exceptions
import aiohttp.client_reqrep
from dotenv import load_dotenv

from bot.colors import red
from bot.constants import URL, timeout

load_dotenv()
response_profile = Optional[List[Dict[str, Any]]]
response_profile_complete = Optional[Dict[str, Any]]

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


async def request_to(url: str) -> response_profile:
    global cookies
    async with aiohttp.ClientSession() as session:
        async with session.get(url, cookies=cookies, timeout=timeout) as response:
            if response.url.host not in URL:  # website page is returned not API (api.www.root-me.org / www.root-me.org)
                return None
            #  purple(f'[{response.status}] {url}')
            if response.status == 200:
                return await response.json()
            elif response.status == 401:
                cookies = await get_cookies()
                return await request_to(url)
            elif response.status == 429:   # Too Many requests
                time.sleep(1)
                return await request_to(url)
            else:
                return None


async def extract_json(url: str) -> response_profile:
    data = await request_to(url)
    if data is None:
        red(url)
    return data


class Parser:

    @staticmethod
    async def extract_rootme_profile(user: str, lang: str) -> response_profile:
        return await extract_json(f'{URL}/auteurs?nom={user}&lang={lang}')

    @staticmethod
    async def extract_rootme_profile_complete(id_user: int) -> response_profile_complete:
        return await extract_json(f'{URL}/auteurs/{id_user}')

    @staticmethod
    async def extract_challenges(lang: str) -> response_profile:
        return await extract_json(f'{URL}/challenges?lang={lang}')

    @staticmethod
    async def extract_challenge_info(id_challenge: Union[int, str]) -> response_profile_complete:
        return await extract_json(f'{URL}/challenges/{id_challenge}')

    @staticmethod
    async def find_challenge(challenge_title: str) -> response_profile_complete:
        return await extract_json(f'{URL}/challenges?titre={challenge_title}')

    @staticmethod
    async def make_custom_query(path: str) -> Any:
        return await extract_json(f'{URL}{path}')
