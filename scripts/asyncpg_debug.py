from __future__ import annotations

import asyncio
import os
import ssl
import sys
import traceback
from urllib.parse import urlparse, unquote

import asyncpg


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")

    parsed = urlparse(dsn)
    print("scheme:", parsed.scheme)
    print("hostname:", parsed.hostname)
    print("port:", parsed.port)
    print("db:", parsed.path)
    if parsed.password is not None:
        print("password_decoded:", unquote(parsed.password))

    ctx = ssl.create_default_context()

    try:
        coro = asyncpg.connect(dsn, ssl=ctx)
        print("connect_coro_type:", type(coro))
        conn = await coro
        try:
            val = await conn.fetchval("SELECT 1")
            print("select1:", val)
        finally:
            await conn.close()
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
