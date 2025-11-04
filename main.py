import asyncio
import json
import os
from datetime import datetime, timezone
from json import dumps
from time import time

from dotenv import load_dotenv

from utils.custom_log_format import logger
from utils.root import get_project_root
from utils.tools import send_request, rnet_client

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
ENC_OID = '0A0EC9DBD18FFD8F8A8B01CA789E5D017D83D628B8C6ADEB5AF505A884969AF4DE9EEA998D172E4ADBBCF5DE50821980EAAA889004855598AF2D87439C81CCEA'
GOT_OID = False
load_dotenv(f'{get_project_root()}/.env')


async def add_num() -> int:
    global count
    async with sem:
        count += 1
        return count


async def send_webhook(webhook_url: str, fields_dict: dict, title: str = "goethe oid Found", color: int = 3447003):
    """
    Sends a rich, timestamped embed to a Discord webhook using httpx.

    Args:
        webhook_url: The Discord webhook URL.
        fields_dict: A dictionary of { "Field Name": "Field Value" }.
        title: The main title of the embed.
        color: The integer value of the embed's left-side color.
    """

    # 1. Get the current time in UTC
    now_utc = datetime.now(timezone.utc)

    # 2. Create the list of "field" objects for the embed
    embed_fields = []

    # Add the "current time" field as requested
    embed_fields.append({
        "name": "Report Time",
        "value": now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
        "inline": False
    })

    # Add all the custom fields from the dictionary
    for name, value in fields_dict.items():
        embed_fields.append({
            "name": name,
            "value": str(value),  # Ensure value is a string
            "inline": False
        })

    # 3. Build the final Discord JSON payload
    payload = {
        "embeds": [
            {
                "title": title,
                "color": color,
                "fields": embed_fields,

                # This is the official Discord timestamp.
                # It must be in ISO 8601 format.
                "timestamp": now_utc.isoformat()
            }
        ]
    }

    # 4. Send the async request.raise_for_status()
    response = await send_request(CLIENT, HEADERS, LOG, webhook_url, json_body=payload, method='POST', return_resp=True)


async def check():
    global GOT_OID
    num = await add_num()
    t1 = time()
    LOG.debug(f"[{num}] - Sending request")
    response = await send_request(
        client=CLIENT,
        log=LOG,
        url='https://www.goethe.de/rest/examfinderv3/exams/institute/O%2010000354'
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
        LOG.debug(f'[{num}] - Got response. {time() - t1:.3f} seconds')
    else:
        LOG.error(f'[{num}] - Not a good response. {time() - t1:.3f} seconds')
        return False

    for data in response['DATA']:
        if data.get('encOID') != ENC_OID:
            continue
        LOG.debug(f'[{num}] - Got encid. len - {len(data)}')
        if oid := data.get('oid', None):
            await send_webhook(
                'https://discord.com/api/webhooks/'
                '1435147515170132060/iL5dvAYyQYQok0YbdQA2pYIOBKjxtqupJCc8fdScGePpqoxE70qq-swqtB8drtqPoqPJ',
                {
                    'oid': oid,
                    'request time': f'{time() - t1:.3f} seconds',
                }
            )
            with open(f'resp.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(response, ensure_ascii=False, indent=4))
            LOG.info(f'[{num}] - Saved response. OID - {oid}. {time() - t1:.3f} seconds')
            GOT_OID = True
            return True
        break
    return False


async def loop():
    while not GOT_OID:
        asyncio.create_task(check())
        await asyncio.sleep(0.05)


if __name__ == '__main__':
    asyncio.run(loop())
