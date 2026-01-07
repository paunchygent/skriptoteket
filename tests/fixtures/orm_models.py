from __future__ import annotations

import importlib
import pkgutil

from skriptoteket.infrastructure.db import models as models_pkg


def load_all_models() -> None:
    """Ensure all ORM models are registered on the SQLAlchemy Base metadata."""
    for module_info in pkgutil.iter_modules(models_pkg.__path__, f"{models_pkg.__name__}."):
        importlib.import_module(module_info.name)
