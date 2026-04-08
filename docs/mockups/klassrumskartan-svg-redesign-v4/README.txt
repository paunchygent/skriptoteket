Klassrumskartan SVG Redesign v4 — "Arkitektens Ritning"

Concept

Teachers are spatial designers of learning environments. The classroom map IS an
architectural drawing. This concept uses real architectural floor-plan conventions
to reinforce the academic identity:

- Double-line walls — the standard cross-section convention for wall thickness
- Door swing arcs — universally understood floor-plan notation
- Dimensional annotations — subtle metre marks give authenticity without clutter
- Graph-paper background — faint 16 px grid, echoing engineering paper
- Fixture fills — whiteboard, kateder, windows get subtle navy fill (8 %) for hierarchy
- Canvas-filled seats — warm `#fafaf6` occupied seats vs dashed empty circles

Why This Beats v3

| Aspect             | v3 ("Stark Wireframe")       | v4 ("Architect's Drawing")                  |
| ------------------ | ---------------------------- | ------------------------------------------- |
| Visual hierarchy   | All stroke, no fill → flat   | Fill layers create depth                    |
| Concept coherence  | Generic wireframe            | Unified architectural metaphor              |
| Hero dead space    | Large empty areas            | Dimension marks + grid fill the margins     |
| Step 01 clarity    | Crosshair (any drawing tool) | Recognisable room with door arc + fixtures  |
| Step 02 clarity    | Confusing split-view transit | Clean list → seat mapping                   |
| Step 03 storytelling | Document + "PDF" text only | Classroom thumbnail inside the document     |
| Brand fit          | Cold, technical              | Warm academic — intellectual and rigorous   |

Technical Notes

- Hero viewBox: `0 0 320 220` (unchanged)
- Step viewBox: `0 0 100 60` (unchanged)
- Colour palette: Navy `#1c2e4a`, Canvas `#fafaf6`, opacity variants only
- Fonts: IBM Plex Mono (labels/fixtures), IBM Plex Sans (names)
- crispEdges: On all rectilinear elements; omitted on circles for smooth rendering
- No Tailwind classes in standalone SVGs (those are added in the Vue component)

Files

| File                           | Replaces                                | Lines in production          |
| ------------------------------ | --------------------------------------- | ---------------------------- |
| `hero-preview.svg`             | `LandingClassroomPreview.vue` L16–254   | 320×220 classroom layout     |
| `step-01-skapa-salen.svg`      | `LandingFeaturedClassroom.vue` L61–92   | 100×60 room creation icon    |
| `step-02-placera-eleverna.svg`  | `LandingFeaturedClassroom.vue` L94–179  | 100×60 student placement icon |
| `step-03-exportera.svg`        | `LandingFeaturedClassroom.vue` L180–226 | 100×60 PDF export icon       |
