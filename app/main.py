from __future__ import annotations

import importlib
import sys
from pathlib import Path

import uvicorn

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

app = importlib.import_module("skriptoteket.web.app").app


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
