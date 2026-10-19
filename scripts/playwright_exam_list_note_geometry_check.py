"""Headless geometry check for the floating printed-total note lines (T11/D3).

TASK-SKRIPT-40-04-10 term T11: the note lines float over the bottom edge of
``.list__scroll`` above a fixed-height footer, and the scroll content always
ends with a one-row end room, so ``scrollHeight`` never changes when a line
appears, goes or returns on undo. Each line stays on one row (ellipsis).

Run from the repository root with the repository's environment::

    pdm run python -m scripts.playwright_exam_list_note_geometry_check

What it does, end to end:
  1. Launches Chromium headless (repo helper first, system Chrome fallback).
  2. Intercepts every /api/** request: the public app bootstrap is
     fulfilled from a fabricated body, everything else is aborted so no
     request ever reaches a real server.
  3. Seeds the guest draft IndexedDB record exactly as the guest store
     writes it, reloads the guest host page, and measures the question
     list for one-line (exam) and two-line (exam plus part) states at
     list widths 440 px and 260 px (via the stored column width the
     resize code reads).
  4. For each width: scrolls ``.list__scroll`` to its end; records
     scrollTop, scrollHeight, clientHeight and the top of every row;
     clicks the Godta glyph; records again; presses the header Angra;
     records again. Asserts all three records are equal (row tops within
     0.5 px), the last row's bottom is above the floating line's top when
     one line shows, and at 260 px the line's height equals one row.
  5. Writes records, assertion output and a PNG of each state under the
     lead's r3 evidence directory; no repository file is touched besides
     this script.

Browser finding (2026-10-19, no install performed): the Playwright-managed
cache (``~/.cache/ms-playwright``) does not exist on this host, and the
repo helper ``scripts/_playwright_browser.py`` only knows a macOS
headless-shell fallback, so ``launch_chromium`` raises here. The host
provides ``/usr/bin/google-chrome`` (154.x), which Playwright drives via
``executable_path`` with ``--no-sandbox``. That fallback is used.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from scripts._playwright_browser import launch_chromium

EVIDENCE = Path(
    "/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions"
    "/01a15330-34cd-7103-bb71-cc8ef9b8a56f/evidence/lead-4ebb41f3/r3"
)

BASE = "http://127.0.0.1:5292"
PAGE_URL = f"{BASE}/public/apps/documents.conversion_hub"
BOOTSTRAP_PATH = "/api/v1/public/apps/documents.conversion_hub"
COLUMN_SIZES_KEY = "skriptoteket.exam-workspace.columns"

GUEST_HOST = '[data-test="exam-workspace-guest-host"]'
QUESTION_LIST = '[data-test="exam-workspace-question-list"]'
PRINTED_LINE = '[data-test="exam-workspace-printed-total-line"]'
CHANGE = '[data-test="exam-workspace-printed-total-change"]'
UNDO = '[data-test="exam-workspace-undo"]'

BOOTSTRAP = {
    "app_id": "documents.conversion_hub",
    "host_mode": "public",
    "public_access_profile": "authenticated_only",
    "summary": "Skapa, redigera och konvertera prov och spara resultatet bland dina filer.",
    "title": "Provhantering",
    "ui_mode": "bespoke_required",
}

SEED_JS = """(record) => new Promise((resolve, reject) => {
  const request = indexedDB.open("skriptoteket_exam_workspace_guest", 1);
  request.onupgradeneeded = () => {
    if (!request.result.objectStoreNames.contains("drafts")) {
      request.result.createObjectStore("drafts");
    }
  };
  request.onsuccess = () => {
    const db = request.result;
    const tx = db.transaction("drafts", "readwrite");
    tx.objectStore("drafts").put(record, "current");
    tx.oncomplete = () => { db.close(); resolve(true); };
    tx.onerror = () => reject(tx.error);
  };
  request.onerror = () => reject(request.error);
})"""


def free_text_item(sequence: int, points: int | None, source: int | None) -> dict:
    return {
        "ai_suggestion": None,
        "import_record": None,
        "facit_text": None,
        "criteria": [],
        "printed_label": None,
        "print_order": [],
        "retry_source": None,
        "answer_key": {"correct_choice_ids": [], "match_pairs": [], "origin": "not_applicable"},
        "body": [
            {
                "heading_level": None,
                "segments": [
                    {
                        "kind": "text",
                        "marks": [],
                        "text": f"Fråga {sequence}: beskriv med egna ord.",
                    }
                ],
            }
        ],
        "choices": [],
        "gaps": [],
        "match_left": [],
        "match_right": [],
        "item_id": f"item_{sequence:03d}",
        "kind": "free_text",
        "points": points,
        "points_estimated": False,
        "review": {
            "confidence": 0.9,
            "parse_origin": "deterministic",
            "reasons": [],
            "state": "review_complete",
        },
        "sequence": sequence,
        "source_anchor": None,
        "source_points": source,
        "suggested_kind": None,
        "tick_points": None,
        "writing_lines": 8,
    }


def paragraph(text: str) -> dict:
    return {"heading_level": None, "segments": [{"kind": "text", "marks": [], "text": text}]}


def make_document(
    document_id: str, printed_total: int | None, items: list[dict], parents: list[dict]
) -> dict:
    return {
        "assets": [],
        "document_id": document_id,
        "header": {"printed_total": printed_total, "tags": []},
        "instructions": [],
        "items": items,
        "origin": {"kind": "created"},
        "parents": parents,
        "revision": 1,
        "schema_version": "native_exam_document_v10",
        "title": "Prov",
    }


def one_line_document() -> dict:
    """One exam line: 15 questions, printed 34, sum 31 (differs by one question's 3 p)."""
    items = [free_text_item(sequence, 2, 2) for sequence in range(1, 15)]
    items.append(free_text_item(15, 3, 3))
    items[0]["points"] = 2
    return make_document("00000000-0000-4000-8000-000000000011", 34, items, [])


def two_line_document() -> dict:
    """Exam line plus one part line: two floating lines stack upward (covering accepted)."""
    items = [free_text_item(sequence, 2, 2) for sequence in range(1, 15)]
    items.append(free_text_item(15, 3, 3))
    parents = [
        {
            "parent_id": "parent_001",
            "item_ids": ["item_001", "item_002"],
            "place": 0,
            "printed_total": 8,
            "instruction": [paragraph("Del 1: Satslösning")],
        }
    ]
    return make_document("00000000-0000-4000-8000-000000000012", 34, items, parents)


def make_record(document: dict) -> dict:
    """A StoredGuestDraft exactly as newGuestDraft + storage shape it."""
    draft = {
        "lineage_id": document["document_id"],
        "saved_document": document,
        "saved_at": "2026-10-19T12:00:00.000Z",
        "cursor": document["document_id"],
        "baseline": {"document": document, "step_id": document["document_id"]},
        "steps": [],
        "position_step_id": document["document_id"],
        "asset_ids": [],
        "notes": [],
    }
    return {"draft": draft, "assets": {}}


MEASURE_JS = """() => {
  const scroll = document.querySelector(".list__scroll");
  const foot = document.querySelector(".list__foot");
  const lines = document.querySelector('[data-test="exam-workspace-printed-total-lines"]');
  const endRoom = document.querySelector('[data-test="exam-workspace-list-end-room"]');
  const rows = Array.from(document.querySelectorAll("[data-entry-id]")).map((row) => {
    const rect = row.getBoundingClientRect();
    return { id: row.getAttribute("data-entry-id"), top: rect.top, bottom: rect.bottom, height: rect.height };
  });
  const rectOf = (element) => {
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return { top: rect.top, bottom: rect.bottom, height: rect.height, width: rect.width };
  };
  const lineBoxes = Array.from(
    document.querySelectorAll('[data-test="exam-workspace-printed-total-line"]'),
  ).map((line) => {
    const rect = line.getBoundingClientRect();
    const text = line.querySelector(".note-line__text");
    const textRect = text ? text.getBoundingClientRect() : null;
    const textStyle = text ? window.getComputedStyle(text) : null;
    return {
      height: rect.height,
      top: rect.top,
      bottom: rect.bottom,
      textHeight: textRect ? textRect.height : null,
      whiteSpace: textStyle ? textStyle.whiteSpace : null,
      overflow: textStyle ? textStyle.overflow : null,
      textOverflow: textStyle ? textStyle.textOverflow : null,
    };
  });
  const linesStyle = lines ? window.getComputedStyle(lines) : null;
  const footStyle = foot ? window.getComputedStyle(foot) : null;
  const scrollStyle = scroll ? window.getComputedStyle(scroll) : null;
  return {
    scrollTop: scroll ? scroll.scrollTop : null,
    scrollHeight: scroll ? scroll.scrollHeight : null,
    clientHeight: scroll ? scroll.clientHeight : null,
    scrollRect: rectOf(scroll),
    footRect: rectOf(foot),
    footHeight: foot ? foot.getBoundingClientRect().height : null,
    linesRect: rectOf(lines),
    linesPresent: !!lines,
    linesInFoot: lines ? !!lines.closest(".list__foot") : null,
    linesPosition: linesStyle ? linesStyle.position : null,
    linesBackground: linesStyle ? linesStyle.backgroundColor : null,
    footChildClasses: foot
      ? Array.from(foot.children).map((child) => child.className) : null,
    endRoomPresent: !!endRoom,
    endRoomHeight: endRoom ? endRoom.getBoundingClientRect().height : null,
    endRoomInScroll: endRoom ? !!endRoom.closest(".list__scroll") : null,
    lineCount: lineBoxes.length,
    lineBoxes,
    rows,
    scrollPosition: scrollStyle ? scrollStyle.position : null,
    footPosition: footStyle ? footStyle.position : null,
  };
}"""

SCROLL_END_JS = """() => {
  const scroll = document.querySelector(".list__scroll");
  if (scroll) scroll.scrollTop = scroll.scrollHeight;
  return scroll ? scroll.scrollTop : null;
}"""


def check_records(name: str, before: dict, after: dict, restored: dict) -> list[str]:
    failures: list[str] = []
    for key in ("scrollTop", "scrollHeight", "clientHeight"):
        values = (before[key], after[key], restored[key])
        if not (values[0] == values[1] == values[2]):
            failures.append(f"{name}: {key} moved: {values[0]} -> {values[1]} -> {values[2]}")
    before_tops = [row["top"] for row in before["rows"]]
    after_tops = [row["top"] for row in after["rows"]]
    restored_tops = [row["top"] for row in restored["rows"]]
    if not (len(before_tops) == len(after_tops) == len(restored_tops)):
        failures.append(
            f"{name}: row count moved: {len(before_tops)} -> {len(after_tops)} -> {len(restored_tops)}"
        )
    else:
        for index, (first, second, third) in enumerate(zip(before_tops, after_tops, restored_tops)):
            if abs(first - second) > 0.5 or abs(first - third) > 0.5:
                failures.append(f"{name}: row {index} top moved: {first} -> {second} -> {third}")
                break
    return failures


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    intercepted: list[str] = []
    records: dict = {}
    failures: list[str] = []

    def handle_route(route) -> None:
        url = route.request.url
        intercepted.append(f"{route.request.method} {url}")
        if urlparse(url).path == BOOTSTRAP_PATH:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BOOTSTRAP))
        else:
            route.abort()

    def load_seeded_page(browser, document: dict, *, list_width: int, expect_lines: bool):
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(120000)
        page.route(lambda url: urlparse(url).path.startswith("/api/"), handle_route)
        page.on(
            "console",
            lambda msg: (
                print(f"[console:{msg.type}] {msg.text[:200]}") if msg.type == "error" else None
            ),
        )
        page.goto(PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_selector(GUEST_HOST, timeout=120000)
        page.evaluate(
            """([key, width]) => localStorage.setItem(key, JSON.stringify({ list: width }))""",
            [COLUMN_SIZES_KEY, list_width],
        )
        page.evaluate(SEED_JS, make_record(document))
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector(GUEST_HOST, timeout=120000)
        page.wait_for_function(
            "() => document.querySelector('[data-test=\"exam-workspace-exam-points\"]')"
            "?.textContent?.includes('Totalt')",
            timeout=120000,
        )
        if expect_lines:
            page.wait_for_selector(PRINTED_LINE, state="visible", timeout=120000)
        return context, page

    def shoot_list(page, name: str) -> None:
        page.locator(QUESTION_LIST).screenshot(path=str(EVIDENCE / f"{name}.png"))

    with sync_playwright() as playwright:
        try:
            browser = launch_chromium(playwright)
            print("browser: repo launch_chromium")
        except Exception as exc:  # noqa: BLE001 - host has no Playwright cache; fall back deliberately
            print(
                f"browser: launch_chromium failed ({exc}); falling back to /usr/bin/google-chrome"
            )
            browser = playwright.chromium.launch(
                headless=True, executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]
            )
            print("browser: system google-chrome fallback")

        for width in (440, 260):
            context, page = load_seeded_page(
                browser, one_line_document(), list_width=width, expect_lines=True
            )
            tag = f"width-{width}"
            page.evaluate(SCROLL_END_JS)
            before = page.evaluate(MEASURE_JS)
            shoot_list(page, f"{tag}-line-shows")
            page.click(CHANGE)
            page.wait_for_selector(PRINTED_LINE, state="detached", timeout=120000)
            page.evaluate(SCROLL_END_JS)
            after = page.evaluate(MEASURE_JS)
            shoot_list(page, f"{tag}-line-gone")
            page.click(UNDO)
            page.wait_for_selector(PRINTED_LINE, state="visible", timeout=120000)
            page.evaluate(SCROLL_END_JS)
            restored = page.evaluate(MEASURE_JS)
            shoot_list(page, f"{tag}-line-restored")
            records[tag] = {"before": before, "after": after, "restored": restored}
            failures.extend(check_records(tag, before, after, restored))

            shown = before
            if shown["rows"]:
                last = shown["rows"][-1]
                if shown["lineBoxes"]:
                    floating_top = shown["lineBoxes"][0]["top"]
                    if not last["bottom"] <= floating_top + 0.5:
                        failures.append(
                            f"{tag}: last row bottom {last['bottom']} covers floating line top {floating_top}"
                        )
            if shown["linesInFoot"] is True:
                failures.append(f"{tag}: lines container sits inside the footer")
            if shown["endRoomPresent"] is not True:
                failures.append(f"{tag}: end-room element missing from the scroll content")
            if width == 260 and shown["lineBoxes"]:
                line_height = shown["lineBoxes"][0]["height"]
                end_room_height = shown["endRoomHeight"]
                if end_room_height is not None and abs(line_height - end_room_height) > 0.5:
                    failures.append(
                        f"{tag}: line height {line_height} != one end-room row {end_room_height}"
                    )
                text_box = shown["lineBoxes"][0]
                if text_box["whiteSpace"] != "nowrap" or text_box["textOverflow"] != "ellipsis":
                    failures.append(
                        f"{tag}: line text not single-row ellipsis "
                        f"(white-space={text_box['whiteSpace']}, text-overflow={text_box['textOverflow']})"
                    )
            context.close()

        context, page = load_seeded_page(
            browser, two_line_document(), list_width=440, expect_lines=True
        )
        page.evaluate(SCROLL_END_JS)
        two = page.evaluate(MEASURE_JS)
        shoot_list(page, "width-440-two-lines")
        records["width-440-two-lines"] = two
        if two["rows"] and len(two["lineBoxes"]) >= 2:
            last = two["rows"][-1]
            topmost = min(box["top"] for box in two["lineBoxes"])
            covers = last["bottom"] > topmost + 0.5
            records["width-440-two-lines"]["covers_last_row"] = covers
            print(f"two-line state covers the last row: {covers} (expected and accepted)")
        else:
            records["width-440-two-lines"]["covers_last_row"] = None
            print("two-line state: could not measure (rows or lines missing)")
        context.close()

        browser.close()

    (EVIDENCE / "geometry-records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "failures": failures,
        "passed": not failures,
        "widths": [440, 260],
        "states": ["line-shows", "line-gone", "line-restored", "two-lines"],
    }
    (EVIDENCE / "geometry-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
