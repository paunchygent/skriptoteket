/**
 * Purpose:
 *   Provide one supported clipboard-write helper for SPA surfaces that need
 *   to copy debug payloads, diff content, or identifiers.
 *
 * Relationships:
 *   - Consumed by editor/debug UI components.
 *   - Intentionally relies on the modern Clipboard API and avoids deprecated
 *     document.execCommand clipboard fallbacks.
 */

export async function writeTextToClipboard(text: string): Promise<boolean> {
  if (!navigator.clipboard?.writeText) {
    return false;
  }

  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
