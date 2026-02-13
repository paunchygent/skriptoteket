PubChem payload mirror (raw)

Location
- Raw payloads are stored under: data/pubchem_payloads/raw/<cid>/

Files per CID
- linkout.json: /rest/pug_view/linkout/compound/<cid>/JSON
- lcss.json: /rest/pug_view/data/compound/<cid>/JSON?toc=LCSS%20TOC
- safety.json: /rest/pug_view/data/compound/<cid>/JSON?heading=Safety%20and%20Hazards
- meta.json: integrity metadata for each stored payload (sha256, bytes, status, content-type, source URL)

Notes
- Raw payloads are written exactly as received (no normalization).
- Integrity metadata is stored alongside each CID so payloads can be validated without rerunning Playwright.
