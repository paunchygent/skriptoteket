from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

from skriptoteket.protocols.llm import (
    ChatOpsProviderProtocol,
    ChatOpsProvidersProtocol,
    ChatStreamProviderProtocol,
    ChatStreamProvidersProtocol,
)


def is_remote_llm_endpoint(base_url: str) -> bool:
    parsed = urlparse(base_url.strip())
    host = parsed.hostname
    if not host:
        return True
    if host in {"localhost"}:
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True

    return not (ip.is_loopback or ip.is_private or ip.is_link_local)


@dataclass(frozen=True, slots=True)
class ChatStreamProviders(ChatStreamProvidersProtocol):
    primary: ChatStreamProviderProtocol
    fallback: ChatStreamProviderProtocol | None
    fallback_is_remote: bool


@dataclass(frozen=True, slots=True)
class ChatOpsProviders(ChatOpsProvidersProtocol):
    primary: ChatOpsProviderProtocol
    fallback: ChatOpsProviderProtocol | None
    fallback_is_remote: bool
