"""Run a coroutine from sync code, whether or not the calling thread has a running loop."""

import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any


def run_blocking[T](coro: Coroutine[Any, Any, T]) -> T:
    """asyncio.run on a fresh thread: never on the caller's loop, never on the app's loop.

    The coroutines may run sync DB queries, so they must not run on the app's event loop.
    """
    with ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, coro).result()
