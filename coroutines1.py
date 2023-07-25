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

logging.basicConfig(level=logging.DEBUG)

MAX_RETRIES = 3

# recursion, may hit limit? though limits are high. What exactly are they?
# can't cleanup in case of error, unable to cancel


async def supervisor(
    url: str, name: str, client: aiohttp.ClientSession, retry: int = 0
) -> int:
    try:
        return await worker(url, name, client)
    except (aiohttp.ServerDisconnectedError, aiohttp.ServerTimeoutError):
        retry += 1
        if retry < MAX_RETRIES:
            # jitter
            await asyncio.sleep(random.random())
            logging.warning("Retrying coroutine %s. Retry: %s", name, retry)
            return await supervisor(url, name, client, retry)

        logging.warning("Retries exhausted for call args %s", (url, client, retry))
        return 0
    except Exception as e:
        logging.error("Irrecoverable error %r.", e)
        logging.error("Failed to finish coroutine %s.", name)
        return 0


# tenacity can be used here
async def worker(url: str, name: str, session: aiohttp.ClientSession) -> int:
    bad_luck = random.random()
    if bad_luck > 0.9:
        logging.warning("Status: failed, name: %s, bad luck: %s", name, bad_luck)
        raise random.choice(
            [aiohttp.ServerDisconnectedError, aiohttp.ServerTimeoutError, RuntimeError]
        )

    async with session.get(url) as response:
        logging.debug(
            "Status: %s, name: %s, bad luck: %s", response.status, name, bad_luck
        )
        return response.status


async def main():
    async with aiohttp.ClientSession() as client:
        start = time.perf_counter()
        coros = [supervisor("https://klichx.dev", str(i), client) for i in range(0, 20)]
        try:
            res = await asyncio.gather(
                *coros,
                return_exceptions=False,
            )
        # If return_exceptions is False, cancelling gather() after it has been
        # marked done won’t cancel any submitted awaitables. For instance,
        # gather can be marked done after propagating an exception to the caller,
        # therefore, calling gather.cancel() after catching an exception
        # (raised by one of the awaitables) from gather won’t cancel
        # any other awaitables.
        except asyncio.CancelledError:
            # can't cancel
            logging.info("CANCEL")
            return

        logging.info("Took %.2f s", time.perf_counter() - start)
        logging.info("Result count %s, and items: %s", len(res), res)


def handle_exception(loop, context):
    # context["message"] will always be there; but context["exception"] may not
    print("yo")
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")


loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
task = loop.create_task(main())
# loop.call_later(1, task.cancel)
loop.run_until_complete(task)
# try:
#     asyncio.run(main())
# except KeyboardInterrupt:
#     logging.info("User cancelled.")
