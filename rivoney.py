# File: rivoney.py
import subprocess
import os
from pathlib import Path

# Resolve absolute paths safely
root_dir = Path(__file__).parent.resolve()
backend_dir = root_dir / "backend"
frontend_dir = root_dir / "frontend"

# Ensure env var is set for the backend process
env = os.environ.copy()
env["DEBUG_GAPS"] = "1"

# Start FastAPI backend
backend_cmd = ["uvicorn", "main:app", "--reload", "--port", "8000"]
backend_proc = subprocess.Popen(backend_cmd, cwd=backend_dir, env=env)

# Start React frontend
frontend_proc = subprocess.Popen(
    ["npm", "start"],
    cwd=frontend_dir,
    shell=True  # This is key for Windows shell commands like npm
)

print("Servers are running...")
print("FastAPI: http://localhost:8000")
print("Frontend: http://localhost:3000")

try:
    backend_proc.wait()
    frontend_proc.wait()
except KeyboardInterrupt:
    print("Shutting down...")
    backend_proc.terminate()
    frontend_proc.terminate()