import asyncio

import pytest

from app.services.capacity import job_capacity


@pytest.mark.asyncio
async def test_job_capacity_allows_only_one_media_job() -> None:
    first_entered = asyncio.Event()
    release_first = asyncio.Event()
    second_entered = asyncio.Event()

    async def first_job() -> None:
        async with job_capacity():
            first_entered.set()
            await release_first.wait()

    async def second_job() -> None:
        await first_entered.wait()
        async with job_capacity():
            second_entered.set()

    first = asyncio.create_task(first_job())
    second = asyncio.create_task(second_job())
    await first_entered.wait()
    await asyncio.sleep(0)

    assert not second_entered.is_set()

    release_first.set()
    await asyncio.gather(first, second)
    assert second_entered.is_set()
