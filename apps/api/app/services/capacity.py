import asyncio
from contextlib import asynccontextmanager, contextmanager
from threading import Semaphore
from typing import AsyncIterator, Iterator


_media_job_capacity = Semaphore(1)


@asynccontextmanager
async def job_capacity() -> AsyncIterator[None]:
    await asyncio.to_thread(_media_job_capacity.acquire)
    try:
        yield
    finally:
        _media_job_capacity.release()


@contextmanager
def sync_job_capacity() -> Iterator[None]:
    _media_job_capacity.acquire()
    try:
        yield
    finally:
        _media_job_capacity.release()
