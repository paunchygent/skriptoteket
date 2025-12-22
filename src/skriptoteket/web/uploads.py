from __future__ import annotations

from fastapi import UploadFile

from skriptoteket.domain.errors import validation_error


async def _read_upload_file_with_limit(*, file: UploadFile, max_bytes: int) -> bytes:
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise validation_error(
            "Uploaded file is too large.",
            details={
                "filename": file.filename,
                "max_bytes": max_bytes,
            },
        )
    return data


async def read_upload_files(
    *,
    files: list[UploadFile],
    max_files: int,
    max_file_bytes: int,
    max_total_bytes: int,
    default_filename: str = "input.bin",
) -> list[tuple[str, bytes]]:
    if not files:
        raise validation_error("At least one file is required.")
    if len(files) > max_files:
        raise validation_error(
            "Too many files uploaded.",
            details={"max_files": max_files, "files": len(files)},
        )

    total_bytes = 0
    input_files: list[tuple[str, bytes]] = []

    for upload in files:
        filename = upload.filename or default_filename
        content = await _read_upload_file_with_limit(file=upload, max_bytes=max_file_bytes)

        total_bytes += len(content)
        if total_bytes > max_total_bytes:
            raise validation_error(
                "Total upload size exceeded.",
                details={"max_total_bytes": max_total_bytes, "total_bytes": total_bytes},
            )

        input_files.append((filename, content))

    return input_files
