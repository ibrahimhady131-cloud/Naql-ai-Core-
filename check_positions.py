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
    rows = await conn.fetch("SELECT time, latitude, longitude, speed_kmh FROM truck_positions WHERE truck_id = '1af055fa-58d9-4624-9ccf-e800580d1f11' ORDER BY time DESC LIMIT 10")
    for r in rows:
        print(f'{r["time"]} | lat={r["latitude"]}, lon={r["longitude"]}, speed={r["speed_kmh"]}')
    await conn.close()

asyncio.run(check())
