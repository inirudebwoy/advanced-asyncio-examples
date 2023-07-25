"""
Handling of task errors, with automated retry
Using as_completed

"""
import asyncio
import logging
import random
import time
import traceback

import aiohttp

logging.basicConfig(level=logging.INFO)

MAX_RETRIES = 3

async def fetch(url: str, session: aiohttp.ClientSession, name: str) -> int:
    if random.random() > 0.9:
        logging.info("Coro %s, Status: boom", name)
        raise RuntimeError

    async with session.get(url) as response:
        logging.info("Coro %s, Status: %s", name, response.status)
        return response.status


async def scheduler(task_definitions):
    tasks = {
        coro(*args, **kwargs): (coro, args, kwargs)
        for coro, args, kwargs in task_definitions
    }
    for coro in asyncio.as_completed(tasks.keys()):
        # failed = False
        # retries = 0
        # while failed or retries < MAX_RETRIES:
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception:
            # failed = True
            # retries += 1
            breakpoint()
            print("Caught exception")
            traceback.print_exc()


# TODO: name to coroutines


async def main():
    async with aiohttp.ClientSession() as client:
        start = time.perf_counter()
        coros = [
            (fetch, ("https://klichx.dev", client, f"fetch no. {i}"), {})
            for i in range(0, 20)
        ]
        await asyncio.create_task(scheduler(coros))
        logging.info("Took %.2f s", time.perf_counter() - start)


asyncio.run(main())
