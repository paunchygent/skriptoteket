from __future__ import annotations

from pathlib import Path
from time import time

from fastapi.templating import Jinja2Templates

from skriptoteket.web.ui_text import run_status_label, version_state_label

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.filters["version_state_label"] = version_state_label
templates.env.filters["run_status_label"] = run_status_label

# Cache-buster for static assets. Changes whenever the server process restarts (dev reload, deploy).
templates.env.globals["static_version"] = str(int(time()))
