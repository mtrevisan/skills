import os, sys, urllib.request
port = os.environ.get("REST_PORT", "8080")
try:
    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3)
    sys.exit(0)
except Exception:
    sys.exit(1)
