/*
Domain purpose:
    Static Swedish fixture for the app shell and exam workspace prototype
    (TASK-SKRIPT-40-04-01). One open exam whose questions together reach every
    state the prototype must show, plus the saved exams the Öppna drawer lists.
    Example wording, courses and central-content items are illustrative.
*/

// The six question types the workspace offers until the ordering decision (R18, T5).
// "Kort svar" is a preset that creates a Lucktext with one empty gap.
window.KINDS = {
  fritext: "Fritext",
  ett: "Flerval: ett val",
  flera: "Flerval: flera val",
  lucktext: "Lucktext",
  rullista: "Lucktext med rullista",
  kategorisera: "Kategorisera",
};
window.NEW_ITEMS = [
  ["fritext", "Fritext"], ["kortsvar", "Kort svar"], ["ett", "Flerval: ett val"], ["flera", "Flerval: flera val"],
  ["lucktext", "Lucktext"], ["rullista", "Lucktext med rullista"], ["kategorisera", "Kategorisera"],
];

window.COURSES = [
  { key: "SVESVE02", name: "Svenska 2", form: "Gymnasiet 2011", mine: true },
  { key: "SVESVE01", name: "Svenska 1", form: "Gymnasiet 2011", mine: true },
  { key: "SVESVE03", name: "Svenska 3", form: "Gymnasiet 2011", mine: false },
  { key: "SVASVA02", name: "Svenska som andraspråk 2", form: "Gymnasiet 2011", mine: false },
  { key: "ENGENG05", name: "Engelska 5", form: "Gymnasiet 2011", mine: false },
  { key: "ENGENG06", name: "Engelska 6", form: "Gymnasiet 2011", mine: false },
  { key: "GRSVE79", name: "Svenska åk 7–9", form: "Grundskolan", mine: false },
];

// Central content for the open exam's course; one tag per bullet (TASK-SKRIPT-39-08-03).
window.CONTENT = {
  SVESVE03: [
    { t: "Litteraturvetenskapliga begrepp och metoder för analys av skönlitteratur", sugg: false, cites: [] },
    { t: "Vetenskapligt skrivande: disposition, språk och källhänvisningar", sugg: false, cites: [] },
    { t: "Svenska och andra språks skönlitteratur från olika epoker", sugg: false, cites: [] },
  ],
  SVESVE02: [
    { t: "Litterära begrepp och berättartekniker, till exempel tillbakablick och inre monolog", sugg: true, cites: ["4a", "4b", "4c"] },
    { t: "Språkriktighet: grammatik, ordval och böjning i egna och andras texter", sugg: true, cites: ["1", "5", "7", "8"] },
    { t: "Analys och tolkning av skönlitteratur, med citat som stöd", sugg: true, cites: ["4b", "10"] },
    { t: "Muntlig och skriftlig argumentation och dess uppbyggnad", sugg: false, cites: [] },
    { t: "Svenska språkets släktskap med grannspråken", sugg: false, cites: [] },
    { t: "Retorikens grunder: syfte, mottagare och situation", sugg: false, cites: [] },
  ],
};

window.EXAMS = [
  { id: "e1", title: "Kursavslutande prov: Svenska 2 – Textanalys och språkriktighet", course: "SVESVE02", saved: "17 okt 14:05", t: 17, exports: { QTI: "17 okt 14:10", PDF: "12 okt 09:30" }, origin: "docx" },
  { id: "e2", title: "Svenska 2 – Retorik och argumentation", course: "SVESVE02", saved: "3 okt 10:12", t: 3, exports: {}, origin: "docx" },
  { id: "e3", title: "Svenska 1 – Novellanalys", course: "SVESVE01", saved: "9 okt 10:12", t: 9, exports: { QTI: "9 okt 10:20" }, origin: "docx" },
  { id: "e4", title: "Prov v.38 – Grammatik", course: "SVESVE01", saved: "21 sep 08:47", t: -9, exports: {}, origin: "docx" },
  { id: "e5", title: "Engelska 5 – Reading comprehension", course: "ENGENG05", saved: "14 sep 13:02", t: -16, exports: { QTI: "14 sep 13:05", DOCX: "14 sep 13:06" }, origin: "digiexam",
    notes: ["Fråga 7 importerades inte: ”Put the events in the right order …” (sortering).", "Fråga 12 importerades inte: ”Draw a line between …” (ritning)."] },
  { id: "e6", title: "Prov v.42", course: null, saved: "15 okt 16:40", t: 15, exports: {}, origin: "digiexam" },
  { id: "e7", title: "Läsförståelse åk 9", course: null, saved: "3 sep 15:30", t: -27, exports: { PDF: "3 sep 15:31" }, origin: "docx" },
];

// Question fields: kind, stem (gaps written {1}, {2} …; a picture as {img}), points (null = missing),
// est (points estimated from the section total), ok (reviewed), keySrc (source | ai | machine | null),
// facit (key wording in the exam file), imp (the Import box), note (a parsing issue).
window.makeExam = () => ({
  id: "e1",
  title: "Kursavslutande prov: Svenska 2 – Textanalys och språkriktighet",
  file: "Kursavslutande prov Svenska 2",
  course: "SVESVE02",
  courseHint: "Svenska 2 (SVESVE02), vt 2026",
  printed: 60,
  origin: "docx",
  tags: [0, 1, 2],
  notes: ["Stycket ”Facit lämnas ut efter provet” är ingen fråga och lästes inte in."],
  items: [
    { k: "q", id: "q1", kind: "ett", stem: "Vilken ordklass är ordet ’snabbt’ i meningen ’Hon sprang snabbt hem’?", points: 1, ok: true, keySrc: "source",
      opts: ["Adverb", "Adjektiv", "Verb", "Substantiv"], key: 0, facit: "1. a",
      imp: { orig: "1. Vilken ordklass är ordet ’snabbt’ i meningen ’Hon sprang snabbt hem’? (1 p)<br>a) Adverb b) Adjektiv c) Verb d) Substantiv", steps: ["Typ: Flerval: ett val", "Facit: kopierat ur provfilen"] } },
    { k: "q", id: "q2", kind: "ett", stem: "Vilket av följande är ett exempel på en metafor?", points: 1, ok: true, keySrc: "ai",
      opts: ["Han är snabb som vinden", "Livet är en resa", "Det regnar ute", "Hon skrattade högt"], key: 1, facit: "Svar: b – livet beskrivs som en resa",
      imp: { orig: "2. Vilket av följande är ett exempel på en metafor? (1 p)<br>a) Han är snabb som vinden b) Livet är en resa c) Det regnar ute d) Hon skrattade högt", steps: ["Typ: Flerval: ett val", "Facit: tolkat av AI ur facittexten"] } },
    { k: "q", id: "q3", kind: "ett", stem: "Vilket ord beskriver bäst textens ton?", points: 1, ok: false, keySrc: "machine", sugg: 1,
      opts: ["Saklig", "Ironisk", "Vardaglig", "Formell"], key: 1, facit: null, note: "Frågetypen kan ha tolkats fel.",
      imp: { orig: "3. Vilket ord beskriver bäst textens ton? (1 p)<br>Saklig – Ironisk – Vardaglig – Formell", steps: ["Typ: Flerval: ett val", "Facit saknades i provfilen; AI föreslog ett", "Skickades om en gång: Fritext → Flerval: ett val"] } },
    { k: "p", id: "p4", text: "Läs novellen ”Vägen hem” av Mira Lind på sidorna 2–3. Svara sedan på frågorna nedan. Citera gärna ur novellen när du motiverar dina svar.", printed: 14,
      imp: { orig: "Uppgift 4 (14 p)<br>Läs novellen ”Vägen hem” av Mira Lind på sidorna 2–3. Svara sedan på frågorna nedan. Citera gärna ur novellen när du motiverar dina svar.", steps: ["Rubriken blev en instruktion med 3 frågor"] },
      kids: [
        { k: "q", id: "q4a", kind: "fritext", stem: "Sammanfatta novellens huvudbudskap med egna ord.", points: 4, ok: true, keySrc: null,
          crit: [["Huvudbudskapet är korrekt återgivet", 2], ["Sammanfattningen är skriven med egna ord", 2]],
          imp: { orig: "a) Sammanfatta novellens huvudbudskap med egna ord. (4 p)<br>Bedömning: huvudbudskap 2 p, egna ord 2 p", steps: ["Typ: Fritext", "Bedömningskriterier lästes ur provfilen"] } },
        { k: "q", id: "q4b", kind: "fritext", stem: "Analysera hur författaren använder bildspråk i andra stycket.", points: 6, ok: true, keySrc: null, crit: [],
          imp: { orig: "b) Analysera hur författaren använder bildspråk i andra stycket. (6 p)", steps: ["Typ: Fritext"] } },
        { k: "q", id: "q4c", kind: "flera", stem: "Vilka två berättartekniker används i novellen?", points: 2, ok: true, keySrc: "source",
          opts: ["Tillbakablick", "Inre monolog", "Brevform", "Allvetande berättare"], key: [0, 1], facit: "c) Tillbakablick, inre monolog",
          imp: { orig: "c) Vilka två berättartekniker används i novellen? (2 p)<br>☐ Tillbakablick ☐ Inre monolog ☐ Brevform ☐ Allvetande berättare", steps: ["Typ: Flerval: flera val", "Facit: kopierat ur provfilen"] } },
      ] },
    { k: "q", id: "q5", kind: "lucktext", stem: "Fyll i rätt form av verbet: Igår {1} (springa) hon till skolan och {2} (äta) lunch med Ali.", points: 2, ok: true, keySrc: "ai",
      gaps: [{ ans: ["sprang"], auto: ["spang", "sprnag"] }, { ans: ["åt"], auto: ["ått"] }], facit: "sprang, åt",
      imp: { orig: "5. Fyll i rätt form av verbet: Igår ______ (springa) hon till skolan och ______ (äta) lunch med Ali. (2 p)", steps: ["Typ: Lucktext", "Facit: tolkat av AI ur facittexten"] } },
    { k: "q", id: "q6", kind: "ett", stem: "Vilket sambandsord passar bäst i meningen ”Hon var trött, ___ gick hon och lade sig”?", points: null, ok: false, keySrc: "source",
      opts: ["därför", "men", "eftersom", "dessutom"], key: 0, facit: "a",
      imp: { orig: "6. Vilket sambandsord passar bäst i meningen ”Hon var trött, ___ gick hon och lade sig”?<br>a) därför b) men c) eftersom d) dessutom", steps: ["Typ: Flerval: ett val", "Facit: kopierat ur provfilen", "Poäng stod inte i provfilen"] } },
    { k: "q", id: "q7", kind: "rullista", stem: "Välj rätt ord: Hon {1} sin bok hemma, {2} fick hon låna en av Elsa.", points: 2, ok: true, keySrc: "source",
      rgaps: [{ opts: ["glömde", "glömt", "glömmer"], key: 0 }, { opts: ["därför", "men", "så"], key: 2 }],
      imp: { orig: "7. Välj rätt ord: Hon (glömde/glömt/glömmer) sin bok hemma, (därför/men/så) fick hon låna en av Elsa. (2 p)", steps: ["Typ: Lucktext med rullista", "Facit: kopierat ur provfilen"] } },
    { k: "q", id: "q8", kind: "kategorisera", stem: "Sortera orden efter ordklass.", ok: true, keySrc: "source", tick: 1,
      grid: { cats: ["Substantiv", "Verb", "Adjektiv"], rows: ["hus", "springa", "vacker", "bok", "läsa"], ticks: [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 0], [0, 1, 0]] },
      imp: { orig: "8. Sortera orden efter ordklass: hus, springa, vacker, bok, läsa. (1 p per rätt)", steps: ["Typ: Kategorisera", "Facit: kopierat ur provfilen"] } },
    { k: "q", id: "q9", kind: "unbuilt", stem: "Rita en tidslinje över novellens händelser och markera vändpunkten med ett kryss.", points: 4, ok: false, keySrc: null,
      imp: { orig: "9. Rita en tidslinje över novellens händelser och markera vändpunkten med ett kryss. (4 p)", steps: ["Typ kunde inte bestämmas", "Konverterades igen som Fritext – blev granskningsfråga"] } },
    { k: "q", id: "q10", kind: "fritext", stem: "Beskriv vad bilden visar och koppla den till novellens tema. {img}", points: 4, est: true, ok: true, keySrc: null, crit: [],
      imp: { orig: "10. Beskriv vad bilden visar och koppla den till novellens tema.<br>[bild: tåg vid perrong i snöfall]", steps: ["Typ: Fritext", "Poängen uppskattades utifrån avsnittets totalpoäng"] } },
    { k: "q", id: "q11", kind: "fritext", suggested: "lucktext", stem: "Skriv rätt form av verbet: Igår ___ (skriva) jag ett långt brev till min mormor.", points: 1, ok: false, keySrc: null, crit: [],
      note: "Frågetypen kan ha tolkats fel.",
      imp: { orig: "11. Skriv rätt form av verbet: Igår ______ (skriva) jag ett långt brev till min mormor. (1 p)", steps: ["Typ: Fritext (provfilen tyder på Lucktext)", "Facit saknas i provfilen"] } },
    { k: "q", id: "q12", kind: "fritext", converting: true, stem: "Förklara skillnaden mellan en novell och en roman. Ge ett exempel på vardera.", points: 3, ok: false, keySrc: null, crit: [],
      imp: { orig: "12. Förklara skillnaden mellan en novell och en roman. Ge ett exempel på vardera. (3 p)", steps: ["Konverteras …"] } },
    { k: "q", id: "q13", kind: "lucktext", stem: "Vad heter novellens huvudperson? {1}", points: 1, ok: true, keySrc: "source", gaps: [{ ans: ["Mira"], auto: [] }], facit: "Mira",
      imp: { orig: "13. Vad heter novellens huvudperson? __________ (1 p)", steps: ["Typ: Lucktext (kort svar)", "Facit: kopierat ur provfilen"] } },
    { k: "q", id: "q14", kind: "fritext", stem: "Skriv en argumenterande text om skoluniformer. Använd minst två argument och ett motargument.", points: 10, ok: true, keySrc: null, crit: [],
      imp: { orig: "14. Skriv en argumenterande text om skoluniformer. Använd minst två argument och ett motargument. (10 p)", steps: ["Typ: Fritext"] } },
  ],
});

// What a QTI export loses in Exam.net (export checklist after QTI export).
window.CHECKLIST = [
  ["4a", "Sammanfatta novellens huvudbudskap …", "Kriterierna följer inte med: Huvudbudskapet är korrekt återgivet (2 p), Sammanfattningen är skriven med egna ord (2 p)"],
  ["5", "Fyll i rätt form av verbet …", "Frågan ger 2 poäng. Varje lucka får 1 poäng."],
  ["8", "Sortera orden efter ordklass.", "Exam.net ger 1 poäng. Sätt 5 poäng."],
];
