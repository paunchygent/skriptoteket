from skriptoteket.domain.scripting.models import ToolVersion


def prepare_execution_env(*, version: ToolVersion) -> dict[str, str]:
    return {
        "HOME": "/tmp/home",
        "XDG_CACHE_HOME": "/tmp/home/.cache",
        "SKRIPTOTEKET_SCRIPT_PATH": "/work/script.py",
        "SKRIPTOTEKET_ENTRYPOINT": version.entrypoint,
        "SKRIPTOTEKET_INPUT_DIR": "/work/input",
        "SKRIPTOTEKET_MEMORY_PATH": "/work/memory.json",
        "SKRIPTOTEKET_OUTPUT_DIR": "/work/output",
        "SKRIPTOTEKET_RESULT_PATH": "/work/result.json",
    }
