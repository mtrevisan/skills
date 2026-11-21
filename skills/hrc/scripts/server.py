"""HRC 4.1 — MCP + REST server. One process, two surfaces.
HRC_MODE:
  stdio → MCP over stdio (Claude Desktop, Cursor, Cline spawn it locally)
  http  → REST on REST_PORT + MCP HTTP on MCP_PORT (default 8080 / 8081)
"""
import os
from fastapi import FastAPI, Header, HTTPException, Depends
from mcp.server.fastmcp import FastMCP
from hrc_engine import run, check

MODE = os.getenv("HRC_MODE", "stdio")
TOKEN = os.getenv("HRC_TOKEN", "")
ENGINE_VERSION = "4.1"

# ---------- Shared internals ----------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _read(fn: str) -> str:
    path = fn if os.path.exists(fn) else os.path.join(BASE_DIR, fn)
    with open(path, encoding="utf-8") as f:
        return f.read()

def _run(payload: dict) -> dict:
    try:
        out = run(payload)
        out["engine_version"] = ENGINE_VERSION
        return out
    except Exception as e:
        return {
            "errors": [f"LINT_ERROR: engine exception - {type(e).__name__}: {e}"],
            "rheology_passed": False, "rheology_errors": [], "notes": [],
            "confidence": "LOW", "penalties": [str(e)],
            "hist_lines": [], "modern_lines": [], "render": {},
            "state": {"python": True, "sig": ""},
            "engine_version": ENGINE_VERSION,
        }

def _check(dossier: str) -> list:
    return [{"level": lv, "message": m} for lv, m in check(dossier)]

# ---------- MCP ----------

mcp = FastMCP("hrc-4.1")

@mcp.tool()
def get_knowledge() -> str:
    """Read KNOWLEDGE.md (K-A…K-G). Call once at the start of every session."""
    return _read("KNOWLEDGE.md")

@mcp.tool()
def get_fallback() -> str:
    """Read FALLBACK.md (F). Use ONLY if run_engine fails or is unreachable."""
    return _read("FALLBACK.md")

@mcp.tool()
def run_engine(payload: dict) -> dict:
    """Run the HRC 4.1 engine on a JSON payload (K-E schema).
    Returns hist_lines, modern_lines, render{telemetry,density,geometry,windows,haccp}, state.sig.
    Paste the lines verbatim. Do not recompute by hand."""
    return _run(payload)

@mcp.tool()
def check_dossier(dossier: str) -> list:
    """Lint the final dossier. Returns [{level:'FAIL'|'WARN', message}].
    Fix every FAIL, then call again. Repeat until 0 FAIL."""
    return _check(dossier)

# ---------- REST ----------

def _auth(authorization: str = Header(default="")):
    if not TOKEN:
        return  # dev mode without token
    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(401, "bad token")

rest = FastAPI(title="HRC 4.1 engine", version=ENGINE_VERSION)

@rest.get("/health")
def health():
    return {"ok": True, "engine": ENGINE_VERSION, "mode": MODE}

@rest.get("/knowledge.md", dependencies=[Depends(_auth)])
def api_knowledge():
    return _read("KNOWLEDGE.md")

@rest.get("/fallback.md", dependencies=[Depends(_auth)])
def api_fallback():
    return _read("FALLBACK.md")

@rest.post("/run", dependencies=[Depends(_auth)])
def api_run(payload: dict):
    return _run(payload)

@rest.post("/check", dependencies=[Depends(_auth)])
def api_check(body: dict):
    if "text" not in body or not isinstance(body["text"], str):
        raise HTTPException(422, "missing or invalid 'text'")
    return _check(body["text"])

# ---------- Entry ----------

if __name__ == "__main__":
    if MODE == "stdio":
        mcp.run()
    else:
        import threading, uvicorn
        rest_port = int(os.getenv("REST_PORT", "8080"))
        mcp_port  = int(os.getenv("MCP_PORT",  "8081"))

        def _serve_rest():
            uvicorn.run(rest, host="0.0.0.0", port=rest_port, log_level="info")

        def _serve_mcp():
            uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0",
                        port=mcp_port, log_level="info")

        t1 = threading.Thread(target=_serve_rest, daemon=True)
        t2 = threading.Thread(target=_serve_mcp,  daemon=True)
        t1.start(); t2.start()
        t1.join();  t2.join()
