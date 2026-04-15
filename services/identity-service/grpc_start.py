import sys
import os
import asyncio

sys.path.insert(0, "F:/Projects-app/BIG-DEV")
sys.path.insert(0, "F:/Projects-app/BIG-DEV/shared")
sys.path.insert(0, "F:/Projects-app/BIG-DEV/services/identity-service")
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.zxnmsjveiymibuuooxwv:EX6kcZ6aCdIe0vBE@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
os.environ["NAQL_SSL_CA_FILE"] = "F:/Projects-app/BIG-DEV/prod-ca-2021.crt"
os.environ["PYTHONPATH"] = "f:/Projects-app/BIG-DEV;f:/Projects-app/BIG-DEV/shared"

from app.grpc_server import serve

if __name__ == "__main__":
    asyncio.run(serve())
