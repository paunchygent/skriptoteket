from __future__ import annotations

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemicalOption,
    ReagentPrepChefChemicalsResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefChemicalsHandlerProtocol,
    ReagentPrepChefHazardStoreProtocol,
)


class ReagentPrepChefChemicalsHandler(ReagentPrepChefChemicalsHandlerProtocol):
    def __init__(self, *, hazards: ReagentPrepChefHazardStoreProtocol) -> None:
        self._hazards = hazards

    async def handle(self, *, actor: User) -> ReagentPrepChefChemicalsResult:
        del actor

        entries = sorted(self._hazards.list_all(), key=lambda item: item.display_name)
        return ReagentPrepChefChemicalsResult(
            chemicals=[
                ReagentPrepChefChemicalOption(
                    key=item.key,
                    display_name=item.display_name,
                    aliases=list(item.aliases),
                )
                for item in entries
            ]
        )
