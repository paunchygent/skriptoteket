from __future__ import annotations

from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefSdsIndexStoreProtocol,
    ReagentPrepChefSdsStoreProtocol,
)


class CachedReagentPrepChefSdsStore(ReagentPrepChefSdsStoreProtocol):
    def __init__(self, *, index: ReagentPrepChefSdsIndexStoreProtocol) -> None:
        self._index = index

    def get(self, *, sds_ref: str) -> tuple[str, bytes, str]:
        return self._index.get_cached(sds_ref=sds_ref)
