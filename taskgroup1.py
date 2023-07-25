"""
Handling of TaskGroup errors
Cancellation is automatic if one of the tasks fails.
May be beneficial for some use cases.

Thoughts:
* automated cleanup in case of error in one of the tasks
* 

"""
import asyncio
import logging
import random
import time

import aiohttp

logging.basicConfig(level=logging.DEBUG)
MAX_RETRIES = 3


async def _fetch(url: str, client: aiohttp.ClientSession) -> int:
    bad_luck = random.random()
    if bad_luck > 0.9:
        logging.info("Status: boom, bad luck: %s", bad_luck)
        raise RuntimeError

    async with client.get(url) as response:
        logging.info("Status: %s, bad luck: %s", response.status, bad_luck)
        return response.status


# TODO: is this a supervisor? it takes care of restarting task
async def fetch(
    url: str, client: aiohttp.ClientSession, tg: asyncio.TaskGroup, retry: int = 0
) -> int:
    try:
        return await _fetch(url, client)
    except RuntimeError:
        if retry < MAX_RETRIES:
            # jitter
            await asyncio.sleep(random.random())
            logging.warning("Retrying coroutine. Retry: %s", retry)
            tg.create_task(fetch(url, client, tg, retry + 1))
            return 0

        logging.warning("Retries exhausted for call args %s", (url, client, retry))
        return 0

async def report(list):
    logging.info("Stuff left %s",len(list))

async def scheduler(task_definitions):
    # automatic cancellation of other tasks
    # something that had to be done manually using tasks
    # or impossible using coroutines?
    tasks = set()
    async with asyncio.TaskGroup() as tg:
        for coro, args, kwargs in task_definitions:
            # TODO: can you shield from cancellation?
            tg.create_task(report(tasks))
            tasks.add(tg.create_task(coro(tg=tg, *args, **kwargs)))

    while tasks:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        tasks.difference_update(done)
        logging.info(f"Still left {len(tasks)}")


async def main():
    async with aiohttp.ClientSession() as client:
        start = time.perf_counter()
        coros = [(fetch, ("https://klichx.dev", client), {}) for _ in range(0, 20)]
        try:
            await asyncio.create_task(scheduler(coros))
        except asyncio.CancelledError:
            logging.info("CANCEL")
        logging.info("Took %.2f s", time.perf_counter() - start)


# loop = asyncio.get_event_loop()
# task = loop.create_task(main())
# loop.call_later(1, task.cancel)
# loop.run_until_complete(task)
try:
    asyncio.run(main())
except KeyboardInterrupt:
    # from the docs
    # Two base exceptions are treated specially: If any task fails
    # with KeyboardInterrupt or SystemExit, the task group still
    # cancels the remaining tasks and waits for them, but then
    # the initial KeyboardInterrupt or SystemExit is re-raised
    # instead of ExceptionGroup or BaseExceptionGroup.
    print("User cancelled")
