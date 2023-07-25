"""
Handling of coroutine errors
works when gather(return_exceptions=True and False)


Thougths:
* quick, with return_exceptions=True might not fail
* not possible to clean up in case of failure
* not possible to interrupt processing
* not able to track execution unless coroutines report output
"""
import asyncio
import logging
import random
import time

import aiohttp

logging.basicConfig(level=logging.INFO)

MAX_RETRIES = 3

# recursion, may hit limit? though limits are high. What exactly are they?
# can't cleanup in case of error, unable to cancel


async def supervisor(
    url: str, name: str, client: aiohttp.ClientSession, retry: int = 0
) -> int:
    try:
        return await worker(url, name, client)
    except RuntimeError:
        retry += 1
        if retry < MAX_RETRIES:
            # jitter
            await asyncio.sleep(random.random())
            logging.warning("Retrying coroutine %s. Retry: %s", name, retry)
            return await supervisor(url, name, client, retry)

        logging.error("Retries exhausted for call args %s", (url, client, retry))
        return 0
    except Exception:
        logging.error("Failed to finish")
        return 0


# tenacity can be used here
async def worker(url: str, name: str, session: aiohttp.ClientSession) -> int:
    bad_luck = random.random()
    if bad_luck > 0.9:
        raise random.choice([RuntimeError, Exception])

    async with session.get(url) as response:
        return response.status


# Python < 3.11 wait would work
async def main():
    async with aiohttp.ClientSession() as client:
        start = time.perf_counter()
        coros = [supervisor("https://klichx.dev", str(i), client) for i in range(0, 40)]
        try:
            res = []
            for i, coro in enumerate(asyncio.as_completed(coros)):
                res.append(await coro)
                print("*" * i, end="\r")
        except asyncio.CancelledError:
            # can't cancel
            logging.info("CANCEL")
            return

        logging.info("Finished")
        logging.info("Took %.2f s", time.perf_counter() - start)
        logging.info("Result %s", res)


# loop = asyncio.get_event_loop()
# task = loop.create_task(main())
# loop.call_later(1, task.cancel)
# loop.run_until_complete(task)
try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.info("User cancelled.")
