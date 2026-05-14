/**
 * Browser artifact download helper for Exam Converter results.
 *
 * Domain purpose:
 *   Convert backend or Gateway served artifact blobs into local browser
 *   downloads while keeping upstream storage and authority out of view code.
 *
 * Relationships:
 *   - Used by both public and authenticated Exam Converter runtime composables.
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
