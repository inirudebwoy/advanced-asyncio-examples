import asyncio
import logging
import random
import time

import aiohttp

logging.basicConfig(level=logging.INFO)

MAX_RETRIES = 3
ASYNCIO_TOTAL_TIMEOUT = 3
HTTP_TIMEOUT = 1


async def supervisor(
    worker,
    url: str,
    name: str,
    client: aiohttp.ClientSession,
    retry: int = 0,
) -> int:
    try:
        return await worker(url, name, client)
    except (
        aiohttp.ServerDisconnectedError,
        aiohttp.ServerTimeoutError,
        asyncio.TimeoutError,
    ):
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
            asyncio.create_task(
                supervisor(worker, "https://klichx.dev", str(i), client)
            )
            for i in range(0, 20)
        ]
        try:
            done, pending = await asyncio.wait(
                coros, timeout=ASYNCIO_TOTAL_TIMEOUT, return_when=asyncio.ALL_COMPLETED
            )
            for t in done:
                logging.info("Task %s done", t.get_name())

            for t in pending:
                logging.info("Task %s pending", t.get_name())
        except asyncio.CancelledError:
            # can't cancel
            logging.info("CANCEL")
            return

        logging.info("Finished")
        logging.info("Took %.2f s", time.perf_counter() - start)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.info("User cancelled.")
