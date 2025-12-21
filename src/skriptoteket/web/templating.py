from __future__ import annotations

from pathlib import Path
from time import time

from fastapi.templating import Jinja2Templates

from skriptoteket.config import Settings
from skriptoteket.web.ui_text import run_status_label, version_state_label
from skriptoteket.web.vite import ViteAssets

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.filters["version_state_label"] = version_state_label
templates.env.filters["run_status_label"] = run_status_label

# Cache-buster for static assets. Changes whenever the server process restarts (dev reload, deploy).
templates.env.globals["static_version"] = str(int(time()))

settings = Settings()
vite = ViteAssets(
    dev_server_url=settings.VITE_DEV_SERVER_URL,
    manifest_path=Path(__file__).resolve().parent / "static" / "spa" / "manifest.json",
    static_base_url="/static/spa",
)
templates.env.globals["vite_tags"] = vite.tags
