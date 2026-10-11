/** Derives a URL-safe tool slug from a tool title, transliterating Swedish letters. */
export function suggestToolSlugFromTitle(title: string): string {
  const lowered = title.trim().toLowerCase();
  const transliterated = lowered
    .replaceAll("å", "a")
    .replaceAll("ä", "a")
    .replaceAll("ö", "o");

  return transliterated
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+/, "")
    .replace(/-+$/, "");
}
