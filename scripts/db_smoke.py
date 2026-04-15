from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from naql_common.db import _normalize_dsn


async def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")

    normalized, connect_args = _normalize_dsn(dsn)
    print("normalized:", normalized)
    print("connect_args:", connect_args)

    engine = create_async_engine(normalized, connect_args=connect_args, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("select1:", result.scalar_one())

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
