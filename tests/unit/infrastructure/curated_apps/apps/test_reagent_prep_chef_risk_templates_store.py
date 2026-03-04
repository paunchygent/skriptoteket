from __future__ import annotations

from pathlib import Path

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import (
    risk_templates_store as risk_templates_store_module,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.risk_templates_store import (
    InMemoryReagentPrepChefRiskTemplateStore,
)


def test_risk_templates_store_loads_templates() -> None:
    templates_path = Path(risk_templates_store_module.__file__).with_name("risk_templates.json")
    store = InMemoryReagentPrepChefRiskTemplateStore(templates_path=templates_path)

    templates = store.get()
    assert templates.generic_risks
    assert templates.hazard_risks
