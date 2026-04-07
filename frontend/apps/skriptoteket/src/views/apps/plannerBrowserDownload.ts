/**
 * Planner browser download helper.
 *
 * This module owns the small shared browser download primitive used by the
 * planner export flows so direct-download guest exports and authenticated job
 * downloads trigger the same DOM-safe attachment behavior.
 */

export function triggerPlannerBrowserDownload(blob: Blob, filename: string): void {
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
