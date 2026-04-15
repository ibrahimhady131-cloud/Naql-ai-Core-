import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host='aws-0-eu-west-1.pooler.supabase.com',
        port=5432,
        user='postgres.zxnmsjveiymibuuooxwv',
        password='EX6kcZ6aCdIe0vBE',
        database='postgres',
        ssl='require'
    )
    rows = await conn.fetch('SELECT id, status, truck_type FROM trucks LIMIT 5')
    for r in rows:
        print(f'{r["id"]} | {r["status"]} | {r["truck_type"]}')
    await conn.close()

asyncio.run(check())
