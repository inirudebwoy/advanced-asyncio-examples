import asyncio
import logging
import random
import time

import aiohttp

logging.basicConfig(level=logging.DEBUG)

MAX_RETRIES = 3
ASYNCIO_TOTAL_TIMEOUT = 3
HTTP_TIMEOUT = 1
WORKERS_COUNT = 20

async def supervisor(
    worker,
    url: str,
    name: str,
    client: aiohttp.ClientSession,
    retry: int = 0,
) -> int:
    try:
        return await worker(url, name, client)
    except (aiohttp.ServerDisconnectedError, aiohttp.ServerTimeoutError):
        retry += 1
        if retry < MAX_RETRIES:
            logging.warning("Retrying coroutine %s. Retry: %s", name, retry)
            return await supervisor(worker, url, name, client, retry)

        logging.warning("Retries exhausted for call args %s", (url, client, retry))
        return 0
    except Exception as e:
        logging.error("Irrecoverable error %r.", e)
        logging.error("Failed to finish coroutine %s.", name)
        return 0


async def worker(url: str, name: str, session: aiohttp.ClientSession) -> int:
    bad_luck: float = random.random()
    if bad_luck > 0.9:
        await asyncio.sleep(10)
        logging.warning("Status: failed, name: %s, bad luck: %.2f", name, bad_luck)
        raise random.choice(
            [aiohttp.ServerDisconnectedError, aiohttp.ServerTimeoutError, RuntimeError]
        )

    async with session.get(url, timeout=HTTP_TIMEOUT) as response:
        logging.debug(
            "Status: %s, name: %s, bad luck: %.2f", response.status, name, bad_luck
        )
        return response.status


async def main():
    async with aiohttp.ClientSession() as client:
        start = time.perf_counter()
        coros = [
            supervisor(worker, "https://klichx.dev", str(i), client)
            for i in range(0, WORKERS_COUNT)
        ]
        try:
            res = await asyncio.gather(
                *coros,
                return_exceptions=False,
            )
        except asyncio.CancelledError:
            logging.info("CANCEL")
            return

        logging.info("Finished")
        logging.info("Took %.2f s", time.perf_counter() - start)
        logging.info("Result count %s, and items: %s", len(res), res)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.info("User cancelled.")
