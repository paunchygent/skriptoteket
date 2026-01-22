from dataclasses import dataclass
from typing import Protocol

from skriptoteket.domain.scripting.models import RunContext, ToolVersion

from .request_factory import RunnerRequestFactoryProtocol
from .result_parser import RunnerResultParserProtocol


@dataclass(frozen=True, slots=True)
class RunnerContract:
    request_factory: RunnerRequestFactoryProtocol
    result_parser: RunnerResultParserProtocol


class RunnerContractSelectorProtocol(Protocol):
    def select(
        self,
        *,
        version: ToolVersion,
        context: RunContext,
    ) -> RunnerContract: ...


@dataclass(frozen=True, slots=True)
class StaticRunnerContractSelector:
    contract: RunnerContract

    def select(
        self,
        *,
        version: ToolVersion,
        context: RunContext,
    ) -> RunnerContract:
        return self.contract
