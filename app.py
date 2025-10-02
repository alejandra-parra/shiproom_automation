# app.py
import os
import sys
import importlib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from mangum import Mangum

# --- Load local secrets and set Google creds path ---
# In Lambda your code is at /var/task (read-only)
load_dotenv(dotenv_path="/var/task/.env", override=True)
print("[DEBUG] Completed: load_dotenv - app.py")
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/var/task/slides_service_account.json")
print(f"[DEBUG] Set GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

# Import your existing CLI module (main.py) without changing it
main_mod = importlib.import_module("main")
print(f"[DEBUG] Set main_mod: {main_mod}")

app = FastAPI()
print(f"[DEBUG] Set app: {app}")

class SlidesRequest(BaseModel):
    # Matches your CLI's --config; defaulting to ./config.yaml as requested
    config_path: str = "./config.yaml"
    # Mirrors your --team flag (optional)
    team: str | None = None
    # Extra room for future parameters (ignored by the CLI but available if you want)
    params: dict | None = None

print("[DEBUG] Defined SlidesRequest class")

@app.post("/report")
def report(req: SlidesRequest, authorization: str | None = Header(None)):
    #Debug
    #print("DEBUG expected SHARED_TOKEN:", repr(os.getenv("SHARED_TOKEN")))
    #print("DEBUG provided Authorization header:", repr(authorization))
    # Optional bearer token check using .env (set SHARED_TOKEN there if you want)
    #expected = os.getenv("SHARED_TOKEN")
    #if expected and authorization != f"Bearer {expected}":
        #raise HTTPException(status_code=401, detail="Unauthorized")

    # Resolve the config path relative to the Lambda bundle
    raw = req.config_path
    print(f"[DEBUG] Set raw: {raw}")
    candidates = []
    print(f"[DEBUG] Set candidates: {candidates}")
    # If caller sent an absolute path, try it first
    if os.path.isabs(raw):
        candidates.append(raw)
        print(f"[DEBUG] Updated candidates (abs): {candidates}")
    else:
        # try as-given (relative to current working dir when running locally)
        candidates.append(os.path.join(os.getcwd(), raw))
        print(f"[DEBUG] Updated candidates (cwd): {candidates}")
        # try relative to this file's directory (useful if you run uvicorn from elsewhere)
        candidates.append(os.path.join(os.path.dirname(__file__), raw))
        print(f"[DEBUG] Updated candidates (file dir): {candidates}")
        # try Lambda's code mount
        candidates.append(os.path.join("/var/task", raw))
        print(f"[DEBUG] Updated candidates (/var/task): {candidates}")
    cfg_path = next((p for p in candidates if os.path.exists(p)), None)
    print(f"[DEBUG] Set cfg_path: {cfg_path}")
    if not cfg_path:
        print(f"[DEBUG] Config not found. Tried: {candidates}")
        raise HTTPException(
            status_code=400,
            detail=f"Config not found. Tried: {', '.join(candidates)}"
        )
    print("[DEBUG] Completed: config path resolution - app.py")

    # Build argv to mimic: python main.py --config <path> [--team <team>]
    argv = ["prog", "--config", cfg_path]
    print(f"[DEBUG] Set argv: {argv}")
    if req.team:
        argv += ["--team", req.team]
        print(f"[DEBUG] Updated argv with team: {argv}")

    # Call your CLI entrypoint exactly as-is, but guard against sys.exit()
    old_argv = sys.argv
    print(f"[DEBUG] Set old_argv: {old_argv}")
    sys.argv = argv
    print(f"[DEBUG] Set sys.argv: {sys.argv}")
    try:
        try:
            main_mod.main()
            print("[DEBUG] Completed: main_mod.main() - app.py")
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 0
            print(f"[DEBUG] Set SystemExit code: {code}")
            if code != 0:
                raise HTTPException(status_code=500, detail=f"CLI exited with code {code}")
            print("[DEBUG] Completed: SystemExit handling in report() - app.py")
    finally:
        sys.argv = old_argv
        print(f"[DEBUG] Restored sys.argv: {sys.argv}")

    print("[DEBUG] Completed: report() - app.py")
    result = {
        "status": "ok",
        "message": "Slides generated",
        "team": req.team,
        "config_path": req.config_path,
    }
    print(f"[DEBUG] Set result: {result}")
    return result

# Lambda entrypoint
handler = Mangum(app)
print(f"[DEBUG] Set handler: {handler}")