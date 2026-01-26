export type ToolSearchCandidate = {
  id: string;
  title: string;
  slug?: string | null;
};

export type ToolSearchResult<T extends ToolSearchCandidate> = T & { score: number };

function normalizeText(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function scoreToken(text: string, token: string, weights: { exact: number; prefix: number; includes: number }): number {
  if (!text || !token) return 0;
  if (text === token) return weights.exact;
  if (text.startsWith(token)) return weights.prefix;
  if (text.includes(token)) return weights.includes;
  return 0;
}

export function searchTools<T extends ToolSearchCandidate>(args: {
  candidates: T[];
  query: string;
  limit?: number;
  locale?: string;
  recencyById?: Map<string, number>;
}): { results: Array<ToolSearchResult<T>>; totalMatches: number; normalizedQuery: string } {
  const normalizedQuery = normalizeText(args.query);
  if (!normalizedQuery) {
    return { results: [], totalMatches: 0, normalizedQuery };
  }

  const tokens = normalizedQuery.split(/\s+/).filter(Boolean);
  if (tokens.length === 0) {
    return { results: [], totalMatches: 0, normalizedQuery };
  }

  const scored: Array<ToolSearchResult<T>> = [];

  for (const candidate of args.candidates) {
    const title = normalizeText(candidate.title);
    const slug = normalizeText(candidate.slug ?? "");
    const haystack = `${title} ${slug}`.trim();

    const matchesAllTokens = tokens.every((token) => haystack.includes(token));
    if (!matchesAllTokens) continue;

    let score = 0;
    for (const token of tokens) {
      score += scoreToken(slug, token, { exact: 240, prefix: 140, includes: 70 });
      score += scoreToken(title, token, { exact: 200, prefix: 110, includes: 55 });
    }

    score += scoreToken(slug, normalizedQuery, { exact: 400, prefix: 220, includes: 90 });
    score += scoreToken(title, normalizedQuery, { exact: 320, prefix: 180, includes: 70 });

    if (score > 0) {
      scored.push({ ...candidate, score });
    }
  }

  const collator = new Intl.Collator(args.locale ?? "sv-SE", { sensitivity: "base" });
  const recency = args.recencyById;

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (recency) {
      const aRecency = recency.get(a.id) ?? null;
      const bRecency = recency.get(b.id) ?? null;
      if (aRecency !== null && bRecency !== null && bRecency !== aRecency) {
        return bRecency - aRecency;
      }
      if (aRecency !== null && bRecency === null) return -1;
      if (aRecency === null && bRecency !== null) return 1;
    }
    return collator.compare(a.title, b.title);
  });

  const totalMatches = scored.length;
  const results = scored.slice(0, args.limit ?? 5);

  return { results, totalMatches, normalizedQuery };
}
