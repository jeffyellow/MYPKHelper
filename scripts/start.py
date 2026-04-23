#!/usr/bin/env python3
"""启动后端服务并在浏览器中打开前端。"""

import subprocess
import sys
import time
import webbrowser
import os


def main():
    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "src")
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

    # Start backend
    print("Starting backend server...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"],
        cwd=backend_dir,
    )

    # Wait for backend to start
    time.sleep(2)

    # Start frontend dev server
    print("Starting frontend dev server...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
    )

    # Wait for frontend
    time.sleep(3)

    # Open browser
    print("Opening browser...")
    webbrowser.open("http://localhost:5173")

    print("\nMYPKHelper is running!")
    print("Backend: http://localhost:8765")
    print("Frontend: http://localhost:5173")
    print("\nPress Ctrl+C to stop.")

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("Stopped.")


if __name__ == "__main__":
    main()
