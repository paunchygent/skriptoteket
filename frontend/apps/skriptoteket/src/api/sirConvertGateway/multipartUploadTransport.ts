/**
 * Sir Convert Gateway multipart upload transport.
 *
 * Domain purpose:
 *   Submit browser-owned multipart conversion requests with upload progress so
 *   large source media transfer is visible before Sir Convert returns a job id.
 *
 * Relationships:
 *   - Used by `client.ts` for transcript audio uploads.
 *   - Reuses Gateway headers prepared by `headers.ts`.
 *   - Returns a standard `Response` for existing parser/error handling.
 */

import { SirConvertGatewayError } from "./errors";
import type { SirConvertUploadProgressHandler } from "./uploadProgress";

export type SirConvertMultipartUploadRequest = {
  body: FormData;
  credentials: "include";
  headers: Headers;
  method: "POST";
  onUploadProgress?: SirConvertUploadProgressHandler;
  signal?: AbortSignal;
  url: string;
};

export type SirConvertMultipartUploadTransport = (
  request: SirConvertMultipartUploadRequest,
) => Promise<Response>;

function uploadAbortedError(): SirConvertGatewayError {
  return new SirConvertGatewayError({
    status: 0,
    code: "SIR_CONVERT_UPLOAD_ABORTED",
    message: "Sir Convert upload was aborted before job admission.",
  });
}

function responseHeadersFromXhr(xhr: XMLHttpRequest): Headers {
  const headers = new Headers();
  const rawHeaders = xhr.getAllResponseHeaders().trim();
  if (!rawHeaders) return headers;
  for (const line of rawHeaders.split(/[\r\n]+/)) {
    const separatorIndex = line.indexOf(":");
    if (separatorIndex <= 0) continue;
    headers.append(
      line.slice(0, separatorIndex).trim(),
      line.slice(separatorIndex + 1).trim(),
    );
  }
  return headers;
}

function emitUploadProgress(
  event: ProgressEvent,
  onUploadProgress: SirConvertUploadProgressHandler | undefined,
): void {
  if (!onUploadProgress) return;
  const totalBytes = event.lengthComputable ? event.total : null;
  onUploadProgress({
    loadedBytes: event.loaded,
    totalBytes,
    percentComplete:
      totalBytes !== null && totalBytes > 0
        ? Math.min(100, Math.max(0, (event.loaded / totalBytes) * 100))
        : null,
  });
}

export async function browserMultipartUploadTransport(
  request: SirConvertMultipartUploadRequest,
): Promise<Response> {
  if (request.signal?.aborted) throw uploadAbortedError();

  return await new Promise<Response>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abortUpload = (): void => {
      xhr.abort();
      reject(uploadAbortedError());
    };

    xhr.open(request.method, request.url, true);
    xhr.withCredentials = request.credentials === "include";
    request.headers.forEach((value, key) => {
      xhr.setRequestHeader(key, value);
    });

    xhr.upload.onprogress = (event) => {
      emitUploadProgress(event, request.onUploadProgress);
    };
    xhr.onload = () => {
      request.signal?.removeEventListener("abort", abortUpload);
      resolve(
        new Response(xhr.responseText, {
          headers: responseHeadersFromXhr(xhr),
          status: xhr.status,
          statusText: xhr.statusText,
        }),
      );
    };
    xhr.onerror = () => {
      request.signal?.removeEventListener("abort", abortUpload);
      reject(
        new SirConvertGatewayError({
          status: xhr.status,
          code: "SIR_CONVERT_UPLOAD_FAILED",
          message: "Sir Convert upload failed before job admission.",
        }),
      );
    };
    xhr.onabort = () => {
      request.signal?.removeEventListener("abort", abortUpload);
      reject(uploadAbortedError());
    };

    request.signal?.addEventListener("abort", abortUpload, { once: true });
    xhr.send(request.body);
  });
}
