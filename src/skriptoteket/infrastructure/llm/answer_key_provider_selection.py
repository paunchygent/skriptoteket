"""Fixed provider-route selection for the answer-key lane.

Purpose:
    Yield the decided Luna-primary/GLM-failover route for every enrichment
    job. The route is fixed at configuration time; the enrichment handler
    owns when the failover profile is actually attempted.

Relationships:
    Implements ``protocols.exam_answer_key.AnswerKeyProviderSelectorProtocol``;
    profiles come from ``infrastructure.llm.openai.answer_key_profiles`` and
    ``infrastructure.llm.openrouter.answer_key_profiles``.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyProviderSelectorProtocol


class FixedRouteAnswerKeyProviderSelector(AnswerKeyProviderSelectorProtocol):
    """Provider selection with exactly one configured route."""

    def __init__(self, *, route: AnswerKeyProviderRoute) -> None:
        self._route = route

    def select_route(self) -> AnswerKeyProviderRoute:
        return self._route
