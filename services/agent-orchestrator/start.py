import sys
import os

# Add paths to sys.path
sys.path.insert(0, "F:/Projects-app/BIG-DEV")
sys.path.insert(0, "F:/Projects-app/BIG-DEV/shared")
sys.path.insert(0, "F:/Projects-app/BIG-DEV/services/agent-orchestrator")
os.environ["PYTHONPATH"] = "F:/Projects-app/BIG-DEV;F:/Projects-app/BIG-DEV/shared"

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)
