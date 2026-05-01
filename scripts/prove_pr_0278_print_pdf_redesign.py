"""Generate real-data PR-0278 Klassrumskartan PDF proof artifacts.

Purpose:
    Build the canonical SA24D/G20 classroom scenario through the production
    export contracts, render workspace and share-link PDFs, and emit first-page
    PNGs plus machine-readable proof metadata for PR-0278 review.

Relationships:
    - Uses the application `poster_scene` and grouping presentation builders.
    - Exercises the infrastructure PDF renderers and share PDF delegation path.
    - Writes review artifacts under `.artifacts/pr-0278-print-pdf-redesign/`.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from unicodedata import normalize
from uuid import UUID, uuid5

from PIL import Image
from pydantic import BaseModel
from pypdf import PdfReader

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportPresentation,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
    build_grouping_export_presentation,
    build_grouping_pdf_view_model,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.translator import (
    translate_workspace_to_poster_scene,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    JsonObject,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.grouping_pdf_renderer import (
    GroupingPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
    BrutalistPosterRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.seating_pdf_renderer import (
    WeasyPrintSeatingPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_pdf_renderer import (
    ExportBackedClassroomPlannerSharePdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    StaticClassroomPlannerShareRenderer,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / ".artifacts/pr-0278-print-pdf-redesign"
GENERATED_AT = datetime(2026, 5, 1, 8, 30, tzinfo=timezone.utc)
NAMESPACE = UUID("cd793e0e-f076-4e4d-b22c-ff965c129a62")
SA24D_STUDENT_NAMES = (
    "Kerstin Aitman",
    "Alva Andblad",
    "Sofia Andersson",
    "Elliot Antonsson",
    "Julia Axelsson",
    "Freja Essle",
    "Hilda Grahn",
    "Inger Isfeldt",
    "Nora Johansson",
    "Nellie Jonson",
    "Ella Kjellman",
    "Alexander Klemets",
    "Lucas Kristiansson",
    "Agnes Leandersson",
    "Molly Neijlind",
    "Petter Odehn",
    "Ellen Odenman",
    "Otilia Olofsson Reijer",
    "Vilma Ossner",
    "Mary Parsons",
    "Julia Post",
    "Lily Sandahl",
    "Nora Schneider",
    "Vincent Strandberg Gunnarsson",
    "Leo Svartling",
    "Moa Svensson",
    "Viktor Thornblad",
    "Linnea Walfridson",
    "Liam Vesterberg",
    "Alma Winald",
    "Edith Winlund Strandler",
)
G20_SEAT_COORDS = (
    (864, 192),
    (960, 192),
    (1056, 192),
    (0, 384),
    (96, 384),
    (192, 384),
    (384, 384),
    (480, 384),
    (576, 384),
    (864, 384),
    (960, 384),
    (1056, 384),
    (0, 576),
    (96, 576),
    (192, 576),
    (384, 576),
    (480, 576),
    (576, 576),
    (864, 576),
    (960, 576),
    (1056, 576),
    (0, 768),
    (96, 768),
    (192, 768),
    (384, 768),
    (480, 768),
    (576, 768),
    (768, 768),
    (864, 768),
    (960, 768),
    (1056, 768),
)
G20_BENCH_POSITIONS = (
    *((x, y) for y in (288, 480, 672) for x in (0, 96, 192)),
    *((x, y) for y in (288, 480, 672) for x in (384, 480, 576)),
    *((x, y) for y in (96, 288, 480, 672) for x in (864, 960, 1056)),
    (768, 672),
)


def main() -> None:
    """Generate proof artifacts for all four teacher-facing PDF paths."""

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = OUTPUT_ROOT / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    roster = _build_roster()
    template = _build_template(owner_user_id=roster.owner_user_id)
    seating_workspace = _build_seating_workspace(roster=roster, template=template)
    grouping_workspace = _build_grouping_workspace(roster=roster)
    seating_contract = _build_seating_contract(workspace=seating_workspace)
    grouping_presentation = build_grouping_export_presentation(workspace=grouping_workspace)

    poster_renderer = BrutalistPosterRenderer()
    seating_pdf_renderer = WeasyPrintSeatingPdfRenderer()
    grouping_pdf_renderer = GroupingPdfRenderer()
    share_pdf_renderer = ExportBackedClassroomPlannerSharePdfRenderer(
        seating_poster_renderer=poster_renderer,
        seating_pdf_renderer=seating_pdf_renderer,
        grouping_pdf_renderer=grouping_pdf_renderer,
    )

    outputs = {
        "workspace-seating": _render_workspace_seating_pdf(
            contract=seating_contract,
            poster_renderer=poster_renderer,
            seating_pdf_renderer=seating_pdf_renderer,
        ),
        "workspace-grouping": _render_workspace_grouping_pdf(
            presentation=grouping_presentation,
            grouping_pdf_renderer=grouping_pdf_renderer,
        ),
        "share-seating": share_pdf_renderer.render(
            artifact=_artifact(
                draft_kind=PlanDraftKind.SEATING,
                presentation_payload=_json_object(seating_contract),
            )
        ),
        "share-grouping": share_pdf_renderer.render(
            artifact=_artifact(
                draft_kind=PlanDraftKind.GROUPING,
                presentation_payload=_json_object(grouping_presentation),
            )
        ),
    }

    proof: dict[str, object] = {
        "scenario": "SA24D / G20",
        "proof_run_id": run_id,
        "proof_output_dir": str(output_dir),
        "generated_at": GENERATED_AT.isoformat(),
        "real_data_counts": {
            "students": len(roster.students),
            "seats": len(seating_contract.poster_scene.seats),
            "fixtures": len(seating_contract.poster_scene.fixtures),
            "groups": len(grouping_presentation.groups),
            "group_members": sum(len(group.members) for group in grouping_presentation.groups),
        },
        "artifacts": {},
    }
    for label, pdf_bytes in outputs.items():
        pdf_path = output_dir / f"{label}.pdf"
        pdf_path.write_bytes(pdf_bytes)
        png_path = _render_first_page_png(pdf_path)
        proof["artifacts"][label] = _inspect_pdf(pdf_path=pdf_path, png_path=png_path)
    artifacts = proof["artifacts"]
    assert isinstance(artifacts, dict)
    proof["renderer_parity"] = {
        "seating_workspace_and_share_png_equal": artifacts["workspace-seating"][
            "first_page_png_sha256"
        ]
        == artifacts["share-seating"]["first_page_png_sha256"],
        "grouping_workspace_and_share_png_equal": artifacts["workspace-grouping"][
            "first_page_png_sha256"
        ]
        == artifacts["share-grouping"]["first_page_png_sha256"],
    }
    proof["share_page_artifacts"] = _write_share_page_artifacts(
        output_dir=output_dir,
        seating_contract=seating_contract,
        grouping_presentation=grouping_presentation,
        roster_id=roster.id,
    )

    proof_path = output_dir / "proof.json"
    proof_path.write_text(
        json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "latest-proof-path.txt").write_text(f"{proof_path}\n", encoding="utf-8")
    print(json.dumps(proof, ensure_ascii=False, indent=2))


def _render_workspace_seating_pdf(
    *,
    contract: PreparedSeatingExportContract,
    poster_renderer: BrutalistPosterRenderer,
    seating_pdf_renderer: WeasyPrintSeatingPdfRenderer,
) -> bytes:
    bundle = poster_renderer.render(
        request=SeatingPosterRenderRequest(
            roster_name=contract.roster_name,
            template_name=contract.template_name,
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
            scene=contract.poster_scene,
        )
    )
    return seating_pdf_renderer.render(bundle=bundle)


def _render_workspace_grouping_pdf(
    *,
    presentation: GroupingExportPresentation,
    grouping_pdf_renderer: GroupingPdfRenderer,
) -> bytes:
    view_model = build_grouping_pdf_view_model(
        presentation=presentation,
        generated_at=GENERATED_AT,
    )
    return grouping_pdf_renderer.render(view_model=view_model)


def _write_share_page_artifacts(
    *,
    output_dir: Path,
    seating_contract: PreparedSeatingExportContract,
    grouping_presentation: GroupingExportPresentation,
    roster_id: UUID,
) -> dict[str, object]:
    """Render real-data immutable share HTML pages and browser PNG proof."""

    renderer = StaticClassroomPlannerShareRenderer()
    grouping_contract = PreparedGroupingExportContract(
        grouping_draft_id=grouping_presentation.draft_id,
        roster_id=roster_id,
        export_kind=GroupingExportKind.PDF,
        paper_size=GroupingExportPaperSize.A4_PORTRAIT,
        presentation=grouping_presentation,
    )
    rendered_pages = {
        "share-page-seating": renderer.render_seating(prepared_export=seating_contract),
        "share-page-grouping": renderer.render_grouping(prepared_export=grouping_contract),
    }
    inspected: dict[str, object] = {}
    for label, rendered in rendered_pages.items():
        html_path = output_dir / f"{label}.html"
        html_path.write_text(rendered.rendered_html, encoding="utf-8")
        png_path = _render_html_png(html_path=html_path)
        inspected[label] = {
            "html": str(html_path),
            "first_page_png": str(png_path),
            "html_sha256": sha256(html_path.read_bytes()).hexdigest(),
            "first_page_png_sha256": sha256(png_path.read_bytes()).hexdigest(),
            "contains_floor_grid_css": "background-image:" in rendered.rendered_css,
            "contains_door_swing_css": ".room-fixture--door::after" in rendered.rendered_css,
            "contains_bench_label": ">Bänk<" in rendered.rendered_html,
            "contains_teacher_fill": "background: rgba(28, 46, 74, 0.86);" in rendered.rendered_css,
            "contains_grouping_ordinal_fill": "background: var(--navy);" in rendered.rendered_css,
        }
    return inspected


def _artifact(
    *,
    draft_kind: PlanDraftKind,
    presentation_payload: JsonObject,
) -> ClassroomPlannerShareArtifact:
    return ClassroomPlannerShareArtifact(
        id=_uuid(f"share-{draft_kind.value}"),
        token_hash="sha256:stored-only",
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=draft_kind,
        owner_user_id=_uuid("owner"),
        draft_id=_uuid(f"draft-{draft_kind.value}"),
        roster_id=_uuid("roster-sa24d"),
        template_id=_uuid("template-g20") if draft_kind is PlanDraftKind.SEATING else None,
        source_revision=1,
        title="SA24D",
        slug=f"sa24d-{draft_kind.value}",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version=f"{draft_kind.value}-share-v1",
        presentation_hash="sha256:presentation",
        content_hash=f"sha256:{draft_kind.value}-content",
        presentation_payload=presentation_payload,
        rendered_html="<html><body>retained share artifact</body></html>",
        rendered_css="body { color: #1c2e4a; }",
        created_at=GENERATED_AT,
        updated_at=GENERATED_AT,
    )


def _build_roster() -> Roster:
    owner_user_id = _uuid("owner")
    return Roster(
        id=_uuid("roster-sa24d"),
        owner_user_id=owner_user_id,
        name="SA24D",
        students=[
            Student(id=_student_id(student_name), display_name=student_name)
            for student_name in SA24D_STUDENT_NAMES
        ],
        created_at=GENERATED_AT,
        updated_at=GENERATED_AT,
    )


def _build_template(*, owner_user_id: UUID) -> RoomTemplate:
    return RoomTemplate(
        id=_uuid("template-g20"),
        owner_user_id=owner_user_id,
        name="G20",
        grid_cols=12,
        grid_rows=9,
        seats=[
            Seat(id=f"seat-{index}", x=x, y=y)
            for index, (x, y) in enumerate(G20_SEAT_COORDS, start=1)
        ],
        fixtures=[
            RoomFixture(
                id=fixture_id,
                type=fixture_type,
                x=x,
                y=y,
                width=width,
                height=height,
                label=label,
            )
            for fixture_id, fixture_type, x, y, width, height, label in (
                ("whiteboard-a", RoomFixtureType.WHITEBOARD, 96, 0, 288, 96, "Whiteboard"),
                ("whiteboard-b", RoomFixtureType.WHITEBOARD, 384, 0, 288, 96, "Whiteboard"),
                ("whiteboard-c", RoomFixtureType.WHITEBOARD, 672, 0, 288, 96, "Whiteboard"),
                ("teacher-desk", RoomFixtureType.TEACHER_DESK, 0, 96, 192, 96, "Kateder"),
                ("door-a", RoomFixtureType.DOOR, 0, 192, 96, 96, None),
                *[
                    (f"bench-{index}", RoomFixtureType.BENCH, x, y, 96, 96, None)
                    for index, (x, y) in enumerate(G20_BENCH_POSITIONS, start=1)
                ],
            )
        ],
        created_at=GENERATED_AT,
        updated_at=GENERATED_AT,
    )


def _build_seating_workspace(
    *,
    roster: Roster,
    template: RoomTemplate,
) -> ClassroomPlannerWorkspace:
    return ClassroomPlannerWorkspace(
        draft=_draft(kind=PlanDraftKind.SEATING, roster=roster, template=template),
        roster=roster,
        template=template,
        seat_assignments=[
            SeatAssignment(student_id=student.id, seat_id=seat.id)
            for student, seat in zip(roster.students, template.seats, strict=True)
        ],
    )


def _build_grouping_workspace(*, roster: Roster) -> ClassroomPlannerWorkspace:
    groups = [
        DraftGroup(
            id=f"group-{index}",
            name=f"Grupp {index}",
            sort_order=index - 1,
            name_is_custom=False,
        )
        for index in range(1, 9)
    ]
    return ClassroomPlannerWorkspace(
        draft=_draft(kind=PlanDraftKind.GROUPING, roster=roster, template=None),
        roster=roster,
        groups=groups,
        group_assignments=[
            GroupAssignment(student_id=student.id, group_id=groups[index % len(groups)].id)
            for index, student in enumerate(roster.students)
        ],
    )


def _build_seating_contract(
    *, workspace: ClassroomPlannerWorkspace
) -> PreparedSeatingExportContract:
    assert workspace.template is not None
    return PreparedSeatingExportContract(
        seating_draft_id=workspace.draft.id,
        roster_id=workspace.roster.id,
        roster_name=workspace.roster.name,
        template_id=workspace.template.id,
        template_name=workspace.template.name,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=translate_workspace_to_poster_scene(workspace=workspace),
    )


def _draft(
    *,
    kind: PlanDraftKind,
    roster: Roster,
    template: RoomTemplate | None,
) -> PlanDraft:
    return PlanDraft(
        id=_uuid(f"draft-{kind.value}"),
        owner_user_id=roster.owner_user_id,
        roster_id=roster.id,
        draft_kind=kind,
        template_id=template.id if template is not None else None,
        status=PlanDraftStatus.ACTIVE,
        revision=1,
        last_opened_at=GENERATED_AT,
        created_at=GENERATED_AT,
        updated_at=GENERATED_AT,
    )


def _render_first_page_png(pdf_path: Path) -> Path:
    prefix = pdf_path.with_suffix("")
    png_path = prefix.with_suffix(".png")
    subprocess.run(
        ["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-png", str(pdf_path), str(prefix)],
        check=True,
    )
    return png_path


def _render_html_png(*, html_path: Path) -> Path:
    """Render one static share HTML page to PNG using the browser engine."""

    from playwright.sync_api import sync_playwright

    png_path = html_path.with_suffix(".png")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.screenshot(path=png_path, full_page=True)
        browser.close()
    return png_path


def _inspect_pdf(*, pdf_path: Path, png_path: Path) -> dict[str, object]:
    reader = PdfReader(str(pdf_path))
    first_page = reader.pages[0]
    text = first_page.extract_text() or ""
    media_box = first_page.mediabox
    return {
        "pdf": str(pdf_path),
        "first_page_png": str(png_path),
        "pdf_sha256": sha256(pdf_path.read_bytes()).hexdigest(),
        "first_page_png_sha256": sha256(png_path.read_bytes()).hexdigest(),
        "png_rendered_from_pdf_sha256": sha256(pdf_path.read_bytes()).hexdigest(),
        "pdf_size_bytes": pdf_path.stat().st_size,
        "first_page_png_size_bytes": png_path.stat().st_size,
        "page_count": len(reader.pages),
        "media_box_points": {
            "width": round(float(media_box.width), 3),
            "height": round(float(media_box.height), 3),
        },
        "contains_logo_footer_text": "skriptoteket.hule.education" in text,
        "contains_share_action_chrome": "Ladda ner PDF" in text,
        "contains_bench_label": "BÄNK" in text.upper(),
        "contains_class_name": "SA24D" in text,
        "contains_room_name": "G20" in text,
        "seat_circle_checks": _seat_circle_checks(png_path) if "seating" in pdf_path.stem else [],
    }


def _seat_circle_checks(png_path: Path) -> list[dict[str, int | bool]]:
    """Measure representative dark seat outlines in the rendered seating PNG."""

    image = Image.open(png_path).convert("RGB")
    pixels = image.load()
    width, height = image.size
    dark_pixels: set[tuple[int, int]] = set()
    for y in range(round(height * 0.25), round(height * 0.62)):
        for x in range(round(width * 0.60), round(width * 0.92)):
            red, green, blue = pixels[x, y]
            if red < 45 and green < 65 and blue < 95:
                dark_pixels.add((x, y))

    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, int, int, int, int]] = []
    for point in list(dark_pixels):
        if point in seen:
            continue
        stack = [point]
        seen.add(point)
        xs: list[int] = []
        ys: list[int] = []
        while stack:
            x, y = stack.pop()
            xs.append(x)
            ys.append(y)
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in dark_pixels and neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        if len(xs) > 1000:
            components.append((len(xs), min(xs), min(ys), max(xs), max(ys)))

    checks: list[dict[str, int | bool]] = []
    for _, min_x, min_y, max_x, max_y in sorted(components, reverse=True):
        box_width = max_x - min_x + 1
        box_height = max_y - min_y + 1
        if box_width < 40 or box_height < 40:
            continue
        checks.append(
            {
                "width_px": box_width,
                "height_px": box_height,
                "square_within_2px": abs(box_width - box_height) <= 2,
            }
        )
        if len(checks) == 3:
            break
    return checks


def _json_object(model: BaseModel) -> JsonObject:
    payload = model.model_dump(mode="json")
    assert isinstance(payload, dict)
    return payload


def _student_id(name: str) -> str:
    normalized = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", "-")


def _uuid(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


if __name__ == "__main__":
    main()
