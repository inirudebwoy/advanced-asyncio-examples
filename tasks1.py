"""
Handling of task errors, with automated retry


Thoughts:
* can track execution with keeping tasks reference
* possible to cancel tasks
* cleanup possible in case of failure

"""
import asyncio
import logging
import random
import time

import aiohttp

logging.basicConfig(level=logging.DEBUG)


async def fetch(url: str, session: aiohttp.ClientSession) -> int:
    if random.random() > 0.9:
        logging.info("Status: boom")
        raise TypeError

    async with session.get(url) as response:
        logging.info("Status: %s", response.status)
        return response.status


async def scheduler(task_definitions):
    tasks = {
        asyncio.create_task(coro(*args, **kwargs)): (coro, args, kwargs)
        for coro, args, kwargs in task_definitions
    }
    while tasks:
        try:
            done, pending = await asyncio.wait(
                tasks.keys(), return_when=asyncio.FIRST_EXCEPTION
            )
        except asyncio.CancelledError:
            # set operations to cancel all the shit
            logging.info("CANCELLLLL")
            # cancel all the tasks
            return

        for task in done:
            coro, args, kwargs = tasks.pop(task)
            # if task.exception() is not None:
            #     task.print_stack()
            #     logging.warning("Retrying coroutine.")
            #     tasks[asyncio.create_task(coro(*args, **kwargs))] = coro, args, kwargs


# TODO: name to coroutines


async def main():
    async with aiohttp.ClientSession() as client:
        start = time.perf_counter()
        coros = [(fetch, ("https://klichx.dev", client), {}) for _ in range(0, 20)]
        await asyncio.create_task(scheduler(coros))
        logging.info("Took %.2f s", time.perf_counter() - start)


async def boom():
    raise ValueError


def handle_exception(loop, context):
    # context["message"] will always be there; but context["exception"] may not
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")


loop = asyncio.new_event_loop()
loop.set_exception_handler(handle_exception)
# task = loop.create_task(main())
loop.create_task(boom())
loop.call_later(3, loop.stop)
loop.run_forever()
# loop.run_until_complete(task)
# try:
#     asyncio.run(main())
# except KeyboardInterrupt:
#     logging.info("User cancelled")
