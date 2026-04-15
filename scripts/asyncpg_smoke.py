from __future__ import annotations

import asyncio
import os

import asyncpg


async def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")

    # If sslmode=require is present, force SSL.
    ssl = True if "sslmode=require" in dsn else None

    conn = await asyncpg.connect(dsn, ssl=ssl)
    try:
        val = await conn.fetchval("SELECT 1")
        print(val)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
