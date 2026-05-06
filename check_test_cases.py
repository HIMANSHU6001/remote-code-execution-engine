import asyncio
from sqlalchemy import select
from db.base import AsyncSessionLocal
from db.models import TestCase

async def check():
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(TestCase.input_data, TestCase.expected_output))
        for r in res.all():
            print(f"Input: {r[0]!r} | Expected: {r[1]!r}")

if __name__ == "__main__":
    asyncio.run(check())
