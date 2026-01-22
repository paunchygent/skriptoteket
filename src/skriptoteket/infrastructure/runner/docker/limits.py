from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DockerRunnerLimits:
    cpu_limit: float
    memory_limit: str
    pids_limit: int
    tmpfs_tmp: str
