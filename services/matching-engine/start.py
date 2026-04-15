import sys
import os

sys.path.insert(0, "F:/Projects-app/BIG-DEV")
sys.path.insert(0, "F:/Projects-app/BIG-DEV/shared")
sys.path.insert(0, "F:/Projects-app/BIG-DEV/services/matching-engine")
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.zxnmsjveiymibuuooxwv:EX6kcZ6aCdIe0vBE@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
os.environ["NAQL_SSL_CA_FILE"] = "F:/Projects-app/BIG-DEV/prod-ca-2021.crt"
os.environ["PYTHONPATH"] = "f:/Projects-app/BIG-DEV;f:/Projects-app/BIG-DEV/shared"

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)
