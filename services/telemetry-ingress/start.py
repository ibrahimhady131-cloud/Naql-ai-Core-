import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.zxnmsjveiymibuuooxwv:EX6kcZ6aCdIe0vBE@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
os.environ["NAQL_SSL_CA_FILE"] = "F:\\Projects-app\\BIG-DEV\\prod-ca-2021.crt"
os.environ["PYTHONPATH"] = "F:\\Projects-app\\BIG-DEV;F:\\Projects-app\\BIG-DEV\\shared"

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8006)
