import asyncio
import inspect
import json
import os
from logging import Logger
from random import choice
from typing import Awaitable
from urllib.parse import urlencode

from dotenv import load_dotenv
from rnet import Client, Proxy, Emulation, Jar, Cookie
from rnet.exceptions import RequestError
from rnet.rnet import Response

from utils.root import get_project_root

load_dotenv(f'{get_project_root()}/.env')
ROTATING_PROXY = os.getenv('ROTATING_PROXY')


def rnet_client(use_proxy: bool = True, allow_redirects: bool = True, set_jar: bool = False) \
        -> Client | tuple[Jar, Client]:
    cookie_store = False
    verify = True
    proxy = []
    if use_proxy:
        proxy = [Proxy.all(ROTATING_PROXY)]
        # proxy = [Proxy.all('http://localhost:8081')]  # for debugging with burp suite or something.
        cookie_store = True
    if os.getenv('PRODUCTION', 'FALSE') == 'TRUE':
        verify = False
    if set_jar:
        jar = Jar()
    orig_headers = [
        "host",
        "cookie",
        "content-length",
        "cache-control",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "origin",
        "content-type",
        "upgrade-insecure-requests",
        "user-agent",
        "accept",
        "sec-fetch-site",
        "sec-fetch-mode",
        "sec-fetch-user",
        "sec-fetch-dest",
        "referer",
        "accept-encoding",
        "accept-language",
        "priority",
        "connection"
    ]
    client = Client(
        emulation=Emulation.Chrome137,
        proxies=proxy,
        verify=verify,
        allow_redirects=allow_redirects,
        timeout=60,
        orig_headers=orig_headers,
        cookie_store=cookie_store
    )
    if set_jar:
        return jar, client
    return client


async def send_request(
        client: Client,
        headers: dict,
        log: Logger,
        url: str,
        timeout: int = 90,
        method: str = 'GET',
        tries: int = 10,
        delay: int | float = 1,
        json_body: dict = None,
        good_statuses: list = None,
        return_json: bool = False,
        return_status: bool = False,
        return_resp: bool = False
) -> str | dict | None | tuple[str, int] | tuple[dict, int] | Response:
    if not good_statuses:
        good_statuses = [200]
    to_return, resp = None, None
    for _ in range(tries):
        try:
            if method == 'GET':
                resp = await client.get(url, headers=headers, timeout=timeout, default_headers=False)
            elif method == 'POST':
                resp = await client.post(url, headers=headers, json=json_body, timeout=timeout, default_headers=False)

            if resp.status.as_int() not in good_statuses:
                log.error(
                    f"Try #{_} - HTTP request failed for {url} - Status Code: {resp.status}")
                return None
            if return_json:
                text = await resp.text()
                to_return = json.loads(text)
            elif return_resp:
                to_return = resp
            else:
                text = await resp.text()
                to_return = text
        except RequestError as e:
            log.error(f"Try #{_} - HTTP request failed for {url}: {e}")
        except Exception as e:
            log.error(f"Try #{_} - HTTP request failed for {url}, Unrecognized error: {e}")
        if to_return:
            if return_status:
                return to_return, resp.status.as_int()
            return to_return
        await asyncio.sleep(delay)
    return None


async def test1():
    client = rnet_client(allow_redirects=False)
    # resp = await client.get('https://httpbin.org/cookies/set?session-id=value&session-token=fuck')
    # print([cookie.name for cookie in resp.cookies])
    # resp = await client.get('https://httpbin.org/cookies/set?session-id=svalue&session-token=sfuck',
    #                         )
    # print([cookie.name for cookie in resp.cookies])
    json_data = {
        'countryCode': 'DE',
        'itemInfo': {
            'asin': 'B0CW2YF59Y',
            'glProductGroupName': 'gl_home',
            'packageLength': '0',
            'packageWidth': '0',
            'packageHeight': '0',
            'dimensionUnit': '',
            'packageWeight': '0',
            'weightUnit': '',
            'afnPriceStr': '59.99',
            'mfnPriceStr': '59.99',
            'mfnShippingPriceStr': '0',
            'currency': 'EUR',
            'isNewDefined': False,
        },
        'programIdList': [
            'Core#0',
            'MFN#1',
        ],
        'programParamMap': {},
    }
    headers = {
        'Sec-Ch-Ua-Platform': '"Windows"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Sec-Ch-Ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'Content-Type': 'application/json; charset=UTF-8',
        'Sec-Ch-Ua-Mobile': '?0',
        'Origin': 'https://sellercentral.amazon.de',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://sellercentral.amazon.de/hz/fba/profitabilitycalculator',
        'Accept-Language': 'en-US,en;q=0.9',
        'Priority': 'u=1, i',
        'Connection': 'keep-alive'
    }
    from utils.custom_log_format import logger
    resp = await send_request(client, url='https://httpbin.org/post', headers=headers, method='POST',
                              json_body=json_data, log=logger(name='test'))
    print(resp)

if __name__ == '__main__':
    asyncio.run(test1())
