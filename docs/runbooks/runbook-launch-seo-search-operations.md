---
type: runbook
id: RUN-launch-seo-search-operations
title: "Runbook: Launch SEO search operations"
status: active
owners: "agents, product-owner, deployment-operator"
created: 2026-04-15
updated: 2026-04-15
system: "skriptoteket-public-search"
---

This runbook is the launch-day operating checklist for Skriptoteket search visibility on the
canonical public app host:

```text
https://skriptoteket.hule.education
```

It complements the runtime crawl fixes from `PR-0267` and the route metadata fixes from `PR-0268`.
It does not replace account-owner action inside Google Search Console or Bing Webmaster Tools.

## Source Check

Official guidance checked on 2026-04-15:

- Google Search Console ownership verification:
  `https://support.google.com/webmasters/answer/9008080?hl=en`
- Google sitemap submission:
  `https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap`
- Google recrawl and URL inspection:
  `https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl`
- Bing Webmaster Tools setup:
  `https://blogs.bing.com/webmaster/June-2025/Start-Using-Bing-Webmaster-Tools-to-Improve-Your-Site-Visibility`
- Bing Search Console import:
  `https://blogs.bing.com/webmaster/september-2019/Import-sites-from-Search-Console-to-Bing-Webmaster-Tools`
- Bing sitemap submission:
  `https://blogs.bing.com/webmaster/may-2022/Spring-cleaning-Removed-Bing-anonymous-sitemap-submission`

## Status Terms

Use these terms in retained evidence:

| Term | Meaning |
|---|---|
| `crawlable and submitted` | The public URLs return correct HTTP/status/metadata, the sitemap is reachable, and the sitemap or URLs have been submitted in the relevant console. |
| `eligible for indexing` | Console inspection reports the URL is accessible, not blocked by robots or `noindex`, and technically acceptable for indexing. |
| `already indexed` | The search provider reports the URL is indexed, or the URL appears in provider-specific search results. |

Do not treat `crawlable and submitted` as `already indexed`. Google documents that recrawling can
take days or weeks and that requesting a crawl does not guarantee immediate or eventual inclusion.
Bing likewise exposes crawl/index diagnostics and sitemap tools, but submission remains an
operator signal rather than a ranking guarantee.

## Preconditions

- `PR-0267` and `PR-0268` are deployed to the canonical public host.
- The operator has account access for Google Search Console and Bing Webmaster Tools.
- The operator has one durable verification path:
  - DNS verification, preferred when DNS access is available.
  - HTML/XML verification file at the site root.
  - Homepage meta tag, only if intentionally added to backend-served initial HTML.
  - Bing import from an already verified Google Search Console property.

## Technical Preflight

Run these from a network outside the server host after deployment:

```bash
BASE_URL="https://skriptoteket.hule.education"

curl -sSI "$BASE_URL/" | sed -n '1,8p'
curl -sSI "$BASE_URL/public/apps/classroom.group-seating-studio" | sed -n '1,8p'
curl -sSI "$BASE_URL/robots.txt" | sed -n '1,8p'
curl -sSI "$BASE_URL/sitemap.xml" | sed -n '1,8p'
curl -sSI "$BASE_URL/this-route-should-not-exist" | sed -n '1,8p'

curl -sS "$BASE_URL/robots.txt"
curl -sS "$BASE_URL/sitemap.xml"
curl -sS "$BASE_URL/" | rg '<title>|name="description"|rel="canonical"|name="robots"|og:url'
curl -sS "$BASE_URL/public/apps/classroom.group-seating-studio" \
  | rg '<title>|name="description"|rel="canonical"|name="robots"|og:url'
```

Expected results:

- `/` returns `200` HTML with the Skriptoteket public metadata from `ST-35-03`.
- `/public/apps/classroom.group-seating-studio` returns `200` HTML with Klassrumskartan metadata.
- `/robots.txt` returns `200`, `text/plain`, and the sitemap URL.
- `/sitemap.xml` returns `200`, XML, and only the two approved public URLs.
- A missing path returns `404` with non-indexable HTML.
- TLS is valid for `skriptoteket.hule.education`.
- Any HTTP or host aliases permanently redirect to the canonical HTTPS host without chains or loops.

## Google Search Console

1. Add or open the property for `https://skriptoteket.hule.education`.
2. Prefer domain/DNS verification if the operator controls the relevant DNS zone. Otherwise use a
   URL-prefix method that matches the deployed host exactly.
3. Verify ownership. Retain only the verification method category and date.
4. Submit `https://skriptoteket.hule.education/sitemap.xml` in the Sitemaps report.
5. Inspect these URLs:
   - `https://skriptoteket.hule.education/`
   - `https://skriptoteket.hule.education/public/apps/classroom.group-seating-studio`
6. Record whether each URL is `crawlable and submitted`, `eligible for indexing`, or
   `already indexed`.
7. If the URL Inspection tool offers request-indexing and the operator has the right role, request
   indexing for the two public URLs once. Do not repeatedly resubmit the same URL.

## Bing Webmaster Tools

1. Add `https://skriptoteket.hule.education`.
2. Verify ownership using one of:
   - Domain Connect if available.
   - XML verification file at the site root.
   - Homepage meta tag in backend-served initial HTML.
   - DNS TXT record.
   - Import from a verified Google Search Console property.
3. Submit or confirm `https://skriptoteket.hule.education/sitemap.xml` under Sitemaps.
4. Use URL Inspection for:
   - `https://skriptoteket.hule.education/`
   - `https://skriptoteket.hule.education/public/apps/classroom.group-seating-studio`
5. Use the robots tester for the same two URLs.
6. Record whether each URL is `crawlable and submitted`, `eligible for indexing`, or
   `already indexed`.

IndexNow remains optional for this launch slice. Add it only through a future backlog item if the
team wants real-time URL submission for content updates.

## Redacted Evidence Template

Use this shape in a retained note or review attachment. Do not paste tokens or account identifiers.

```markdown
## Launch SEO Search Operations Evidence

- Date:
- Operator role or initials:
- Canonical host: `https://skriptoteket.hule.education`
- Deployed version/reference:
- Technical preflight:
  - DNS:
  - TLS:
  - Redirects:
  - `/robots.txt`:
  - `/sitemap.xml`:
  - `/`:
  - `/public/apps/classroom.group-seating-studio`:
  - missing path:
- Google Search Console:
  - Property type:
  - Verification method category:
  - Verification result:
  - Sitemap submitted:
  - `/` inspection:
  - `/public/apps/classroom.group-seating-studio` inspection:
  - Follow-up date:
- Bing Webmaster Tools:
  - Site URL:
  - Verification method category:
  - Verification result:
  - Sitemap submitted:
  - `/` inspection:
  - `/public/apps/classroom.group-seating-studio` inspection:
  - Follow-up date:
- Blockers:
```

Allowed evidence:

- status labels
- timestamps
- operator initials or role
- verification method category
- redacted screenshots with account identifiers cropped or blurred

Forbidden evidence:

- raw DNS/HTML/XML/meta verification token values
- unredacted account emails
- cookies or session URLs
- API keys
- screenshots that expose account identifiers

## Host Migration Rerun

If the canonical host changes:

1. Update `PUBLIC_APP_BASE_URL`.
2. Deploy crawler files and metadata for the new host.
3. Add permanent redirects from the old public URLs to the new canonical URLs.
4. Re-run the technical preflight for old and new hosts.
5. Add or verify new Google and Bing properties as required.
6. Submit the new sitemap and inspect both public URLs.
7. Retain a redacted migration note using the evidence template above.
