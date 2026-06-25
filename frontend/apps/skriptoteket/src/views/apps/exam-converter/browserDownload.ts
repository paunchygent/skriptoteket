/**
 * Browser artifact download helper for conversion app results.
 *
 * Domain purpose:
 *   Convert backend or Gateway served result blobs into local browser
 *   downloads while keeping upstream storage and authority out of view code.
 *
 * Relationships:
 *   - Used by Exam Converter, transcript, and Document Converter runtimes.
 */

export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
