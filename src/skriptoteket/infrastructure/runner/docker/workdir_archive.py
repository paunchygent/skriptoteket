from __future__ import annotations

import io
import tarfile

from skriptoteket.domain.scripting.models import ToolVersion


def build_workdir_archive(
    *,
    version: ToolVersion,
    input_files: list[tuple[str, bytes]],
    memory_json: bytes,
) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        script_bytes = version.source_code.encode("utf-8")

        script_info = tarfile.TarInfo(name="script.py")
        script_info.size = len(script_bytes)
        script_info.mode = 0o644
        tar.addfile(script_info, io.BytesIO(script_bytes))

        memory_info = tarfile.TarInfo(name="memory.json")
        memory_info.size = len(memory_json)
        memory_info.mode = 0o644
        tar.addfile(memory_info, io.BytesIO(memory_json))

        input_dir_info = tarfile.TarInfo(name="input")
        input_dir_info.type = tarfile.DIRTYPE
        input_dir_info.mode = 0o755
        input_dir_info.size = 0
        tar.addfile(input_dir_info)

        for safe_name, content in input_files:
            input_path = f"input/{safe_name}"
            input_info = tarfile.TarInfo(name=input_path)
            input_info.size = len(content)
            input_info.mode = 0o644
            tar.addfile(input_info, io.BytesIO(content))

    return tar_buffer.getvalue()
