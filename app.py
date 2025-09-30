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
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/var/task/slides_service_account.json")

# Import your existing CLI module (main.py) without changing it
main_mod = importlib.import_module("main")

app = FastAPI()


class SlidesRequest(BaseModel):
    # Matches your CLI's --config; defaulting to ./config.yaml as requested
    config_path: str = "./config.yaml"
    # Mirrors your --team flag (optional)
    team: str | None = None
    # Extra room for future parameters (ignored by the CLI but available if you want)
    params: dict | None = None


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
    candidates = []
    # If caller sent an absolute path, try it first
    if os.path.isabs(raw):
        candidates.append(raw)
    else:
        # try as-given (relative to current working dir when running locally)
        candidates.append(os.path.join(os.getcwd(), raw))
        # try relative to this file's directory (useful if you run uvicorn from elsewhere)
        candidates.append(os.path.join(os.path.dirname(__file__), raw))
        # try Lambda's code mount
        candidates.append(os.path.join("/var/task", raw))
    cfg_path = next((p for p in candidates if os.path.exists(p)), None)
    if not cfg_path:
        raise HTTPException(
            status_code=400,
            detail=f"Config not found. Tried: {', '.join(candidates)}"
        )

    # Build argv to mimic: python main.py --config <path> [--team <team>]
    argv = ["prog", "--config", cfg_path]
    if req.team:
        argv += ["--team", req.team]

    # Call your CLI entrypoint exactly as-is, but guard against sys.exit()
    old_argv = sys.argv
    sys.argv = argv
    try:
        try:
            main_mod.main()
        except SystemExit as e:
            # Treat sys.exit() from your CLI as success unless it signaled an error
            code = e.code if isinstance(e.code, int) else 0
            if code != 0:
                raise HTTPException(status_code=500, detail=f"CLI exited with code {code}")
    finally:
        sys.argv = old_argv

    return {
        "status": "ok",
        "message": "Slides generated",
        "team": req.team,
        "config_path": req.config_path,
    }


# Lambda entrypoint
handler = Mangum(app)