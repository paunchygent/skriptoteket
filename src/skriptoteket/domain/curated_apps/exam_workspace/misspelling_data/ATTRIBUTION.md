# Exam-workspace misspelling data

The JSON maps and compressed word-form lists in this directory are generated
static data. The producer reads them locally; requests never download sources,
run a model, or start a spell-checking service.

## Sources and attribution

`BUILD.json` records every exact source URL, SHA-256, generated pair count and
word-form count. LibreOffice inputs are pinned to commit
`67032ee957631908098a72edf48dc81cac27e369`; Wikipedia inputs use exact revisions.

- **Swedish learner errors:** DaLAJ-GED-Superlim 2.0, Språkbanken Text and the
  SweLL/DaLAJ contributors, DOI `10.23695/KXVZ-TX42`, CC BY 4.0. Only explicit
  single-word `O` and mixed-`O` confusion pairs are included. Pure `O` pairs
  outrank mixed labels.
- **Swedish editor errors:** Swedish Wikipedia contributors, *Lista över
  vanliga språkfel*, revision `59163295`, and *AutoWikiBrowser/Typos*, revision
  `59749383`, CC BY-SA 4.0. LÖVS contributes explicit written forms in the
  spelling sections, not guessed expansions of suffix shorthand. AWB contributes
  only plain or single-group rules; multi-group Cartesian inventions are excluded.
- **English learner errors:** Roger Mitton, Birkbeck spelling-error corpus,
  `missp.dat`. Repeated rows contribute observed frequency, below source tier.
- **English editor errors:** English Wikipedia contributors, *Lists of common
  misspellings/For machines*, revision `1199637275`, CC BY-SA. Ambiguous
  multiple-correction rows are excluded.
- **Swedish REP/word forms:** LibreOffice Swedish dictionary by Göran Andersson
  and contributors (`sv_SE`, LGPLv3).
- **English REP/word forms:** LibreOffice `en_US`, SCOWL by Kevin Atkinson and
  contributors, including the Ispell-derived dictionary notices (SCOWL/BSD).
- **Keyboard maps:** repository-authored symmetric neighbours from vendored
  Swedish and English staggered QWERTY rows; they are not frequency evidence.

Licensing analysis is outside this task; these notes preserve attribution.
The optional research supplements DaLAJ v1 O-Comp and UD-SweLL are not included
in this build. The primary DaLAJ 2.0 sources already supply the learner tier.

## Build and ranking

From the repository root, provide a private raw-input directory:

```bash
pdm run build-answer-misspellings --raw-dir /path/to/private/raw
pdm run build-answer-misspellings --raw-dir /path/to/private/raw --check
```

The build downloads missing inputs and verifies every checksum. It stops on a
checksum mismatch instead of silently accepting source drift. The second
command regenerates in memory and compares all five payloads without changing
them. Compression uses a fixed zero timestamp.

Ranking is source tier first (learner, then editor/bot), observed pair frequency
second, and lexical order last. The runtime keeps that order, then tries one
REP reversal and keyboard neighbours. REP tuples retain the affix-file column
order `(misspelling, correction)`; generation matches the correction column and
substitutes the misspelling column. Anchors constrain the word boundary; dot,
whitespace and underscore rules do not run.

Both build and runtime reject dictionary word forms, not merely stems. The
committed lexicons expand the pinned dictionaries' prefix/suffix rules and
cross products, including inflections such as Swedish `katternas` and English
`walked`. The runtime checks changed words inside phrases too. These are finite
lexicons: they do not enumerate all productive compounds assembled by Hunspell
at lookup time, or words missing from the source dictionaries. By user decision
2026-10-15, no compound or linking-s check is applied: a candidate forming a real
compound absent from the committed lexicon is not filtered.

Every attested pair is pre-filtered through the repository A10 bound. All
runtime tiers pass the same bound and the complete current item gold-answer
exclusion. JSON maps and word lists are cached once per language per process,
including simultaneous first requests.
