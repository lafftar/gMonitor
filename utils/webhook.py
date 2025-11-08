import asyncio
import datetime
import os

from dotenv import load_dotenv

from utils.custom_log_format import logger
from utils.tools import rnet_client, send_request

load_dotenv()
LOG = logger(name='DISCORD')
SEM = asyncio.Semaphore(2)
client = rnet_client(use_proxy=False)
headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'tjaycodes'
}


async def send_webhook(
        fields_dict: dict,
        webhook_url: str = os.getenv('DISCORD_WEBHOOK'),
        title: str = "Stock Alert",
        color: int = 3066993,
        inline_fields: bool = True
):
    formatted_fields = []
    thumbnail = None
    url = None
    for name, value in fields_dict.items():
        if name == 'image':
            thumbnail = str(value)
            continue
        if name == 'url':
            url = str(value)
        formatted_fields.append({
            "name": str(name).upper(),
            "value": str(value),
            "inline": inline_fields
        })

    payload = {
        "embeds": [
            {
                "title": title,
                "color": color,
                "fields": formatted_fields,
                "thumbnail": {"url": thumbnail},
                "url": url,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "footer": {
                    "text": "Coded by [tjaycodes.] <- Add Me."
                }
            }
        ]
    }

    async with SEM:
        if not fields_dict.get('error'):
            await asyncio.gather(
                # *[
                    send_request(
                        client,
                        log=LOG,
                        method='POST',
                        url=webhook_url,
                        headers=headers,
                        json_body=payload,
                        good_statuses=[200, 204]
                    )
                    # send_request(
                    #     client,
                    #     log=LOG,
                    #     method='POST',
                    #     url='https://discord.com/api/webhooks/1436313224533508159/'
                    #         'UX1IrCY3FSCfrXrNJ70izw47-eELWsy9TstvMppsKonPNzbCV-bC8JuWNqKEEDUYwatV',
                    #     headers=headers,
                    #     json_body=payload,
                    #     good_statuses=[200, 204]
                    # )
                # ]
            )
        else:
            await send_request(
                client,
                log=LOG,
                method='POST',
                url=webhook_url,
                headers=headers,
                json_body=payload,
                good_statuses=[200, 204]
            )
    LOG.info(f'Webhook sent successfully - {fields_dict.get("title") or fields_dict.get("event name") or "Error"}')

if __name__ == '__main__':
    asyncio.run(send_webhook({'test': 'test'}))