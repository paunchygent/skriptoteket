"""DI bindings for the Flunk-Out Frenzy curated app.

Flunk-Out Frenzy only needs its bootstrap handler binding.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.flunk_out_frenzy import GetFlunkOutFrenzyBootstrapHandler
from skriptoteket.protocols.flunk_out_frenzy import FlunkOutFrenzyBootstrapHandlerProtocol


class FlunkOutFrenzyProvider(Provider):
    """Provide the Flunk-Out Frenzy bootstrap handler."""

    @provide(scope=Scope.REQUEST)
    def flunk_out_frenzy_bootstrap_handler(self) -> FlunkOutFrenzyBootstrapHandlerProtocol:
        return GetFlunkOutFrenzyBootstrapHandler()
