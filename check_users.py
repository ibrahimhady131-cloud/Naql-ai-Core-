import asyncio
import os
from sqlalchemy import text
from naql_common.db.deps import init_cockroach

async def check():
    db_url = os.getenv("DATABASE_URL")
    db = init_cockroach(db_url)
    async with db.engine.connect() as conn:
        # Check invoices for recent shipments
        result = await conn.execute(text("SELECT id, shipment_id, total_amount_egp, status FROM invoices ORDER BY created_at DESC LIMIT 3"))
        rows = result.fetchall()
        print("Recent invoices:")
        for row in rows:
            print(f"  ID: {row[0]}, Shipment: {row[1]}, Amount: {row[2]} EGP, Status: {row[3]}")

asyncio.run(check())
