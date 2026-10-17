/** Browser clipboard boundary shared by authenticated and public planner links. */
export const SHARE_COPY_RECOVERY_MESSAGE =
  "Länken finns kvar. Använd Kopiera för att försöka igen.";

export async function copyShareTextToClipboard(value: string): Promise<boolean> {
  try {
    if (!navigator.clipboard) {
      return false;
    }
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    // Permission denial does not invalidate the server-created link.
    return false;
  }
}
