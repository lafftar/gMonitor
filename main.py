import asyncio
import os
from asyncio import sleep
from datetime import datetime, timezone
from random import randint
from time import time

from dotenv import load_dotenv

from utils.custom_log_format import logger
from utils.root import get_project_root
from utils.tools import send_request, rnet_client
from utils.webhook import send_webhook

LOG = logger(name="gMonitor")
CLIENT = rnet_client(use_proxy=False)
HEADERS = {
    "host": "www.goethe.de",
    "sec-ch-ua-platform": 'Windows"',
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "accept": "*/*",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://www.goethe.de/ins/in/en/spr/prf/gzb2.cfm",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=1, i",
    'x-forwarded-for': '23.39.75.168',
}
count = 0
sem = asyncio.Semaphore(1)
OIDS = set()
load_dotenv(f'{get_project_root()}/.env')


def load_oids():
    """Loads once at the start of the program."""
    with open('oids.txt', 'r', encoding='utf-8') as f:
        for code in f.readlines():
            if not code.strip():
                continue
            OIDS.add(code.strip())


def write_oids():
    """Writes at end of program"""
    with open('oids.txt', 'w') as f:
        for product_code in OIDS:
            f.write(f'{product_code}\n')


async def add_num() -> int:
    global count
    async with sem:
        count += 1
        return count


async def check():
    num = await add_num()
    t1 = time()
    LOG.debug(f"[{num}] - Sending request")
    response = await send_request(
        client=CLIENT,
        log=LOG,
        url='https://www.goethe.de/rest/examfinderv3/exams/institute'
            '/O%2010000353%2CO%2010000354%2CO%2010000355%2CO%2010000356%2CO%2010000357%2CO%2010000358'
            '?langId=1'
            '&sortField=startDate'
            '&langIsoCodes=en'
            '&countryIsoCode=in'
            '&sortOrder=ASC'
            '&formstruct[category]=E007'
            '&category=E007'
            f'&count={os.getenv("COUNT", "1")}'
            '&start=1'
            '&formstruct[type]=ER'
            '&page=1',
        headers=HEADERS,
        return_json=True
    )
    if response.get('LANGID'):
        if len(response.get('DATA')) != int(os.getenv("COUNT", "1")):
            LOG.error(f'[{num}] - Got response. {(time() - t1) * 1000:.1f} ms. Data Len - {len(response.get('DATA'))}')
        else:
            LOG.debug(f'[{num}] - Got response. {(time() - t1) * 1000:.1f} ms. Data Len - {len(response.get('DATA'))}')
    else:
        LOG.error(f'[{num}] - Not a good response. {(time() - t1) * 1000:.1f} ms. Data Len - {len(response.get('DATA'))}')
        return False

    ts = (time() - t1) * 1000
    for data in response['DATA']:
        oid = data.get('oid', None)
        if not oid or oid in OIDS:
            continue
        OIDS.add(oid)
        LOG.debug(f'[{num}] - Got encid. len - {len(data)}')
        asyncio.create_task(send_webhook(
            webhook_url='https://discord.com/api/webhooks/'
            '1435147515170132060/iL5dvAYyQYQok0YbdQA2pYIOBKjxtqupJCc8fdScGePpqoxE70qq-swqtB8drtqPoqPJ',
            fields_dict={
                'event name': data.get('eventName', 'null'),
                'location': data.get('locationName', 'null'),
                'availability': data.get('availability', 'null'),
                'encOID': data.get('encOID', 'null'),
                'oid': oid,
                'request time': f'{ts:.1f} ms. Data Len - {len(response.get('DATA'))}',
            },
            title='OID Found'
        ))
        # with open(f'resp.json', 'w', encoding='utf-8') as f:
        #     f.write(json.dumps(response, ensure_ascii=False, indent=4))
        LOG.info(f'[{num}] - Saved response. OID - {oid}. {ts:.1f} ms. '
                 f'Data Len - {len(response.get('DATA'))}')
    return False


async def loop():
    load_oids()
    while True:
        # await check()
        asyncio.create_task(check())
        await asyncio.sleep(float(os.getenv("SLEEP", 0.5)))


if __name__ == '__main__':
    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        LOG.info("Keyboard interrupt detected. Exiting.")
    finally:
        write_oids()
