/*
Domain purpose:
    Behaviour for the app shell and exam workspace prototype
    (TASK-SKRIPT-40-04-01). Static data from data.js, no backend. Implements
    the save model (Spara, Spara som, autosave steps), 10-step undo and redo,
    the keyboard shortcuts, the drawers, menus and every planned control, and
    reads a URL hash so each reviewed state can be opened directly.
*/
(() => {
const $ = (id) => document.getElementById(id);
const g = (n, cls = "") => `<svg class="g ${cls}" aria-hidden="true"><use href="#i-${n}"/></svg>`;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const MAC = /Mac|iPhone|iPad/.test(navigator.platform);
const MOD = MAC ? "⌘" : "Ctrl+";
const SHIFT = MAC ? "⇧" : "Shift+";
const kbd = (k, shift = false) => (MAC ? `${shift ? SHIFT : ""}${MOD}${k}` : `${MOD}${shift ? SHIFT : ""}${k}`);
const phoneMq = matchMedia("(max-width: 767px)");
const deskMq = matchMedia("(min-width: 1280px)");
const HIST_MAX = 10;
const now = () => { const d = new Date(); return `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`; };

// ───────── State ─────────
const S = {
  view: "workspace", exam: null, saved: "", savedAt: "17 okt 14:05", sel: null, drawer: null,
  impOpen: false, prefOpen: false, undo: [], redo: [], typing: null, saving: false,
  importing: null, sort: "kurs", fmt: "QTI", dest: "download", checklist: false,
  busyAll: false, tagsBusy: false, gapPop: null, curGap: null, courseQuery: null,
};
const snap = () => JSON.stringify(S.exam);
const dirty = () => !!S.exam && snap() !== S.saved;
const examRow = () => EXAMS.find((x) => x.id === S.exam?.id);
const course = (k) => COURSES.find((c) => c.key === k);

function entries() {
  const out = []; let n = 0;
  for (const it of S.exam?.items ?? []) {
    n++;
    out.push({ it, lab: String(n), parent: null });
    if (it.k === "p") it.kids.forEach((c, j) => out.push({ it: c, lab: `${n}${"abcdefghij"[j]}`, parent: it }));
  }
  return out;
}
const entry = (id) => entries().find((e) => e.it.id === id);
const qs = () => entries().filter((e) => e.it.k === "q");
function pts(q) {
  if (q.kind === "kategorisera") return q.grid.ticks.flat().filter(Boolean).length * (q.tick ?? 0);
  if (q.kind === "fritext" && q.crit?.length) return q.crit.reduce((s, c) => s + (+c[1] || 0), 0);
  return q.points;
}
const sum = (list) => list.reduce((s, q) => s + (pts(q) ?? 0), 0);
const kindName = (q) => (q.kind === "unbuilt" ? "Ej konverterad" : KINDS[q.kind]);
function blockers(q) {
  const b = [];
  if (q.converting) return ["konverteras fortfarande"];
  if (q.kind === "unbuilt" && !q.ok) b.push("kunde inte konverteras");
  if (pts(q) === null || pts(q) === undefined) b.push("poäng saknas");
  if (q.keySrc === "machine" && !q.ok) b.push("facit ej granskat");
  if ((q.kind === "ett" || q.kind === "flera") && q.opts.some((o) => !o.trim())) b.push("ett alternativ saknar text");
  if (q.kind === "rullista" && q.rgaps.some((r) => r.key === null || r.opts.some((o) => !o.trim()))) b.push("en rullista är inte klar");
  if (q.kind === "lucktext" && q.gaps.some((x) => !x.ans.length) && q.gaps.some((x) => x.ans.length)) b.push("en lucka saknar svar");
  return b;
}

// ───────── History: each autosave is one step; at most 10; continues past Spara ─────────
function step() {
  S.undo.push(snap()); if (S.undo.length > HIST_MAX) S.undo.shift();
  S.redo = [];
}
function typingStep() {
  if (!S.typing) step();
  clearTimeout(S.typing); S.typing = setTimeout(() => { S.typing = null; renderHeader(); }, 900);
}
function restore(json) {
  S.exam = JSON.parse(json);
  if (!entry(S.sel)) S.sel = qs()[0]?.it.id ?? null;
  render();
}
function undo() { if (!S.undo.length) return; clearTimeout(S.typing); S.typing = null; S.redo.push(snap()); restore(S.undo.pop()); hideToast(); }
function redo() { if (!S.redo.length) return; S.undo.push(snap()); restore(S.redo.pop()); }

// ───────── Save model ─────────
function save() {
  if (!S.exam) return;
  S.saving = true; renderHeader();
  setTimeout(() => {
    S.saving = false; S.saved = snap();
    const d = new Date(); S.savedAt = `${d.getDate()} okt ${now()}`;
    const r = examRow(); if (r) { r.saved = S.savedAt; r.t = 99; r.title = S.exam.title; }
    render(); toast("Provet är sparat.", { glyph: "circle-check" });
  }, 450);
}
function openSaveAs(err = false) {
  closeMenus();
  $("sa-name").value = `${S.exam.title} (kopia)`;
  $("sa-err").hidden = !err; $("sa-name").setAttribute("aria-invalid", String(err));
  if (err) $("sa-name").value = EXAMS[1].title;
  $("scrim").hidden = false; $("dlg-saveas").hidden = false; $("sa-name").focus(); $("sa-name").select();
}
function closeSaveAs() { $("scrim").hidden = true; $("dlg-saveas").hidden = true; }
function confirmSaveAs() {
  const name = $("sa-name").value.trim();
  if (!name || EXAMS.some((x) => x.title === name)) { $("sa-err").hidden = false; $("sa-name").setAttribute("aria-invalid", "true"); return; }
  const copy = JSON.parse(snap());
  copy.id = `e${Date.now()}`; copy.title = name; copy.file = name.replace(/[:–]/g, "").replace(/\s+/g, " ");
  S.savedAt = `17 okt ${now()}`;
  EXAMS.unshift({ id: copy.id, title: name, course: copy.course, saved: S.savedAt, t: 100, exports: {}, origin: copy.origin });
  S.exam = copy; S.saved = snap(); S.undo = []; S.redo = [];
  closeSaveAs(); render(); toast(`Kopian är öppen: ${name}`, { glyph: "circle-check" });
}

// ───────── Shell ─────────
const NAV = [
  ["home", "house", "Hem"], ["browse", "library", "Katalog"], ["vault", "folder", "Mina filer"],
  ["mytools", "wrench", "Mina verktyg"], ["suggest", "lightbulb", "Föreslå verktyg"], ["profile", "circle-user-round", "Profil"],
  ["-", "", "Administration"],
  ["admintools", "settings", "Hantera verktyg"], ["review", "clipboard-check", "Granska förslag"], ["users", "users", "Användare"],
];
function renderNav() {
  $("nav-items").innerHTML = NAV.map(([id, icon, label]) => id === "-" ? `<div class="nav-sec">${label}</div>`
    : `<button class="nav-item" data-nav="${id}" title="${label}" ${S.view === id ? 'aria-current="page"' : ""}>${g(icon)}<span>${label}</span></button>`).join("");
}
function setView(v) {
  S.view = v; document.body.classList.remove("nav-open"); $("b-nav").setAttribute("aria-expanded", "false");
  const ws = v === "workspace";
  $("ws").hidden = !ws; $("plain").hidden = ws; $("brand-app").hidden = !ws;
  document.body.classList.toggle("in-ws", ws);
  renderNav();
  if (!ws) renderPlain();
}
function renderPlain() {
  const label = NAV.find((n) => n[0] === S.view)?.[2] ?? "Hem";
  let body;
  if (S.view === "vault") {
    body = `<div class="vault">${EXAMS.map((x) => {
      const ex = Object.entries(x.exports).map(([f, t]) => `<div class="vrow sub">${g(f === "QTI" ? "file-up" : "file-text", "sm")}<span><div class="t">${esc(fileName(x.title, f))}</div><div class="m">${f} · sparad ${t}</div></span><span class="chip">${f}</span></div>`).join("");
      return `<div class="vrow">${g("file-text")}<span><div class="t">${esc(x.title)}</div><div class="m">Prov · sparat ${x.saved}${x.course ? ` · ${course(x.course).name}` : ""}</div></span><button class="btn compact" data-open-exam="${x.id}">Öppna</button></div>${ex}`;
    }).join("")}</div>`;
  } else if (S.view === "home") {
    body = `<div class="vault"><div class="vrow">${g("file-text")}<span><div class="t">Provredigering</div><div class="m">Importera, granska och exportera prov</div></span><button class="btn compact" data-nav="workspace">Öppna</button></div></div>
      <p class="hint" style="margin-top:16px">${g("info", "sm")}Sidans innehåll behåller sin nuvarande layout (ST-SKRIPT-40-03). Prototypen visar bara ramen.</p>`;
  } else {
    body = `<div class="stub">Sidans innehåll behåller sin nuvarande layout och får de delade komponenterna i ST-SKRIPT-40-03.<br>Prototypen visar sidramen: rubrik, ingress och innehållsytan.</div>`;
  }
  const lead = S.view === "vault" ? "Dina sparade filer. Ett prov visar sina exporter direkt under sig." : "Sidram för alla vanliga sidor.";
  $("plain").innerHTML = `<div class="inner"><h1>${label}</h1><p class="lead">${lead}</p>${body}</div>`;
}
const fileName = (title, f) => `${title.replace(/[:–]/g, "").replace(/\s+/g, " ").trim()}.${f === "QTI" ? "zip" : f.toLowerCase()}`;

// Phone: the exam title and Spara move into the top bar's page slot.
function placeForWidth() {
  const ph = phoneMq.matches;
  if (ph) { $("tb-slot").append($("titleblock"), $("save-split")); }
  else { $("wshead").prepend($("titleblock")); $("b-open").after($("save-split")); }
  if (!ph) { document.body.classList.remove("nav-open", "show-list"); }
  renderEditor();
}

// ───────── Header ─────────
function renderHeader() {
  const has = !!S.exam;
  $("title-text").textContent = has ? S.exam.title : "Inget prov öppet";
  $("b-title").disabled = !has;
  const c = has && course(S.exam.course);
  const total = has ? sum(qs().map((e) => e.it)) : 0;
  const st = S.saving ? `<span class="st">${g("loader-circle", "sm spin")}Sparar …</span>`
    : dirty() ? `<span class="st dirty" title="Ändringarna sparas automatiskt som utkast. Spara skriver över provet i Mina filer.">${g("pencil-line", "sm")}Osparat</span>`
    : `<span class="st" title="Provet i Mina filer har alla ändringar">${g("check", "sm")}Sparat ${S.savedAt}</span>`;
  $("meta").innerHTML = has ? `${st}<span class="dot"></span><span>${c ? `${c.name} · ${c.key}` : "Utan kurs"}</span><span class="dot"></span><span>${total} p</span>` : "";
  for (const id of ["b-save", "b-save-menu", "b-export", "b-ai-all"]) $(id).disabled = !has;
  $("b-save").title = `Spara (${kbd("S")})`; $("b-save").setAttribute("aria-keyshortcuts", MAC ? "Meta+S" : "Control+S");
  $("b-undo").disabled = !S.undo.length; $("b-redo").disabled = !S.redo.length;
  $("b-undo").title = S.undo.length ? `Ångra (${kbd("Z")})` : "Inget att ångra";
  $("b-redo").title = S.redo.length ? `Gör om (${kbd("Z", true)})` : "Inget att göra om";
  $("b-ai-all").disabled = !has || S.busyAll;
  $("b-new").disabled = !has;
  $("b-ai-all").title = S.busyAll ? "Facitförslagen tas fram …" : "Föreslå facit för frågor som saknar facit";
  $("ai-all-glyph").innerHTML = `<use href="#i-${S.busyAll ? "loader-circle" : "sparkles"}"/>`; $("ai-all-glyph").classList.toggle("spin", S.busyAll);
  $("b-title").setAttribute("aria-expanded", String(S.drawer === "meta"));
  $("b-open").setAttribute("aria-expanded", String(S.drawer === "open"));
  document.querySelectorAll("[data-kbd]").forEach((k) => (k.textContent = kbd(k.dataset.kbd)));
}

// ───────── Question list ─────────
function rowMeta(q) {
  const b = blockers(q), p = pts(q);
  const ptxt = p === null || p === undefined ? "" : `${p} p`;
  if (q.converting) return "Konverteras …";
  if (b.length) return `${kindName(q)} · <span class="bad">${b[0]}</span>`;
  return `${kindName(q)} · ${ptxt}`;
}
const plain = (s) => s.replace(/\{img\}/g, "[bild]").replace(/\{\d+\}/g, "___");
function renderRows() {
  if (!S.exam) { $("rows").innerHTML = ""; $("list-count").textContent = "Frågor"; $("listfoot").innerHTML = ""; return; }
  const all = entries();
  $("list-count").textContent = `Frågor (${qs().length})`;
  $("rows").innerHTML = all.map(({ it, lab, parent }) => {
    const sel = it.id === S.sel ? " sel" : "";
    if (it.k === "p") {
      const sub = sum(it.kids);
      return `<div class="row prow${sel}" data-id="${it.id}" role="button" tabindex="-1"><span class="n">${lab}</span><span><div class="t">${esc(it.text)}</div><div class="m">Instruktion · ${it.kids.length} ${it.kids.length === 1 ? "fråga" : "frågor"} · ${sub} p</div></span><span></span>
        <span>${it.printed && it.printed !== sub ? `<span class="warn" title="Tryckt delsumma ${it.printed} p, frågorna ger ${sub} p">${g("triangle-alert", "sm")}</span>` : ""}</span></div>`;
    }
    const q = it;
    const ai = q.keySrc === "ai" ? `<span class="ai" title="Tolkad av AI">${g("sparkles", "sm")}</span>` : q.keySrc === "machine" ? `<span class="ai" title="Förslag från AI">${g("sparkles", "sm")}</span>` : "<span></span>";
    const stt = q.converting ? `<span class="muted" title="Konverteras">${g("loader-circle", "sm spin")}</span>`
      : q.ok && !blockers(q).length ? `<span class="ok" title="Granskad">${g("circle-check", "sm")}</span>` : `<span class="warn" title="Behöver granskas">${g("triangle-alert", "sm")}</span>`;
    return `<div class="row${parent ? " child" : ""}${q.converting ? " converting" : ""}${sel}" data-id="${q.id}" role="button" tabindex="-1"><span class="n">${lab}</span><span><div class="t">${esc(plain(q.stem)) || "Ny fråga"}</div><div class="m">${rowMeta(q)}</div></span>${ai}${stt}</div>`;
  }).join("");
  const total = sum(qs().map((e) => e.it));
  $("listfoot").innerHTML = `<span class="grow">Totalt <b>${total} p</b></span>${S.exam.printed && S.exam.printed !== total ? `<span class="tsig" title="Tryckt totalsumma ${S.exam.printed} p, frågorna ger ${total} p">${g("triangle-alert", "sm")}Provet anger ${S.exam.printed} p</span>` : ""}`;
}

// ───────── Editor ─────────
function stemHtml(q) {
  return esc(q.stem).replace(/\{img\}/g, '<span class="pic" contenteditable="false" role="img" aria-label="Bild"></span>').replace(/\{(\d+)\}/g, (_, n) => {
    const i = +n - 1;
    if (q.kind === "rullista") { const r = q.rgaps[i]; const v = r?.key !== null && r?.key !== undefined ? r.opts[r.key] : "välj rätt";
      return `<span class="gap${r?.key === null ? " empty" : ""}" contenteditable="false" data-gap="${i}" title="Lucka ${n}: rullista">${g("chevron-down", "sm")}<span class="gn">${n}</span>${esc(v || "–")}</span>`; }
    const x = q.gaps?.[i]; const v = x?.ans.length ? x.ans.join(" / ") : `Lucka ${n}`;
    return `<span class="gap${x && !x.ans.length ? " empty" : ""}" contenteditable="false" data-gap="${i}" role="button" aria-haspopup="dialog" aria-expanded="${S.gapPop === i}" title="${x?.ans.length ? `Lucka ${n}, godkända svar: ${esc(x.ans.join(", "))}` : `Lucka ${n}, saknar godkända svar`}"><span class="gn">${n}</span>${esc(v)}</span>`;
  });
}
function readStem(ed) {
  let s = "";
  ed.childNodes.forEach((n) => {
    if (n.nodeType === 3) s += n.textContent;
    else if (n.classList?.contains("gap")) s += `{${+n.dataset.gap + 1}}`;
    else if (n.classList?.contains("pic")) s += "{img}";
    else s += n.textContent;
  });
  return s.replace(/\s+/g, " ");
}
const marks = () => `<div class="marks" role="toolbar" aria-label="Formatering">
  ${[["bold", "Fet", "B"], ["italic", "Kursiv", "I"], ["underline", "Understruken", "U"]].map(([c, t, k]) => `<button class="btn compact icon" data-mark="${c}" title="${t} (${kbd(k)})" aria-label="${t}">${g(c, "sm")}</button>`).join("")}
  ${[["superscript", "Upphöjd"], ["subscript", "Nedsänkt"]].map(([c, t]) => `<button class="btn compact icon" data-mark="${c}" title="${t}" aria-label="${t}">${g(c, "sm")}</button>`).join("")}
  <span class="msep"></span>
  ${[1, 2, 3].map((n) => `<button class="btn compact icon" data-mark="h${n}" title="Rubrik ${n}" aria-label="Rubrik ${n}">${g(`heading-${n}`, "sm")}</button>`).join("")}</div>`;

function importBox(it, lab) {
  if (!it.imp) return "";
  const src = S.exam.origin === "digiexam" ? "DigiExam" : "Word";
  const q = it.k === "q" ? it : null;
  const retry = q && q.imp && !q.converting ? `<div class="retry"><span class="muted" style="font-size:12px">Konvertera frågan igen som</span>
    <select aria-label="Frågetyp">${Object.entries(KINDS).map(([k, v]) => `<option value="${k}" ${k === (q.kind === "unbuilt" ? "fritext" : q.kind) ? "selected" : ""}>${v}</option>`).join("")}</select>
    <button class="btn compact" data-act="retry">${g("rotate-cw", "sm")}Konvertera igen</button></div>` : "";
  return `<div class="imp-wrap${S.impOpen ? " open" : ""}" ${S.impOpen ? "" : "inert"}><div><div class="imp">
    <h3>I provfilen <span class="src">· ${src}</span></h3><div class="orig">${it.imp.orig}</div>
    ${q?.facit ? `<h3 style="margin-top:10px">Facit i provfilen</h3><div class="orig">${esc(q.facit)}</div>` : ""}
    ${q?.note ? `<p class="issue">${g("triangle-alert", "sm")}${q.note}</p>` : ""}
    <ol class="steps">${it.imp.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>${retry}</div></div></div>`;
}
function qtoolsHtml(it, isQ) {
  const imp = it.imp ? `<button class="btn${S.impOpen ? " pressed" : ""}" data-act="import" aria-expanded="${S.impOpen}" title="Visa frågan som den står i provfilen">${g("file-text")}<span class="word">Import</span></button>` : "";
  const chk = isQ ? `<button class="btn icon${it.ok ? " filled-check" : ""}" data-act="review" aria-pressed="${it.ok}" title="${it.ok ? "Ångra granskad" : "Markera som granskad"}" aria-label="${it.ok ? "Ångra granskad" : "Markera som granskad"}" ${it.converting ? "disabled" : ""}>${g("check")}</button>` : "";
  return imp + chk;
}
function renderEditor() {
  const ed = $("editor");
  if (!S.exam) {
    ed.innerHTML = `<div class="empty">${g("folder-open", "lg")}<h2>Inget prov öppet</h2><p>Importera ett prov från Word eller DigiExam, eller öppna ett sparat prov.</p><button class="btn" data-act="open">${g("folder-open")}Öppna</button></div>`;
    $("phone-tools").innerHTML = ""; $("p-pos").textContent = "Inget prov"; $("p-state").innerHTML = ""; return;
  }
  const e = entry(S.sel) ?? qs()[0]; if (!e) return;
  S.sel = e.it.id;
  const { it, lab, parent } = e;
  $("p-pos").textContent = `Fråga ${lab}`;
  if (it.k === "p") {
    $("p-state").innerHTML = g("book-open", "sm");
    $("phone-tools").innerHTML = qtoolsHtml(it, false);
    const sub = sum(it.kids);
    ed.innerHTML = `<div class="in"><div class="qhead"><h1 class="qnum">Fråga ${lab}</h1><span class="typebtn" style="cursor:default">Instruktion</span>
      <div class="qtools"><span class="phone-hide" style="display:contents">${qtoolsHtml(it, false)}</span></div></div>
      ${importBox(it, lab)}
      <div class="label" style="margin-top:0">Instruktion</div>
      <div class="rich">${marks()}<div class="ed" contenteditable="true" spellcheck="false" data-field="ptext">${esc(it.text)}</div></div>
      <div class="label"><span class="grow">Deluppgifter</span><button class="btn compact" data-act="addchild" aria-haspopup="menu" aria-expanded="false">${g("plus", "sm")}Deluppgift</button></div>
      <div class="kids">${it.kids.map((c, j) => `<div class="kid"><span class="muted">${lab}${"abcdefghij"[j]}</span>
        <button class="open" data-goto="${c.id}"><span class="ex">${esc(plain(c.stem)) || "Ny fråga"}</span><span class="m">${kindName(c)}</span></button>
        <span class="pts">${pts(c) ?? "–"} p</span>
        <span class="ctl"><button class="rm" data-kid-up="${j}" ${j === 0 ? "disabled" : ""} title="Flytta upp" aria-label="Flytta upp">${g("arrow-up", "sm")}</button>
        <button class="rm" data-kid-down="${j}" ${j === it.kids.length - 1 ? "disabled" : ""} title="Flytta ned" aria-label="Flytta ned">${g("arrow-down", "sm")}</button>
        <button class="rm" data-kid-del="${j}" ${it.kids.length === 1 ? 'disabled title="En instruktion behöver minst en deluppgift"' : 'title="Ta bort deluppgiften"'} aria-label="Ta bort deluppgiften">${g("trash-2", "sm")}</button></span></div>`).join("")}</div>
      <p class="psum"><span>Totalt ${sub} p. Poängen sätts på varje deluppgift.</span>${it.printed && it.printed !== sub ? `<span class="tsig">${g("triangle-alert", "sm")}Tryckt delsumma ${it.printed} p, frågorna ger ${sub} p</span>` : ""}</p></div>`;
    return;
  }
  const q = it;
  $("p-state").innerHTML = q.converting ? g("loader-circle", "sm spin") : `<span class="${q.ok && !blockers(q).length ? "ok" : "warn"}">${g(q.ok && !blockers(q).length ? "circle-check" : "triangle-alert", "sm")}</span>`;
  $("phone-tools").innerHTML = qtoolsHtml(q, true);
  const lock = q.converting ? 'aria-disabled="true"' : "";
  const unbuilt = q.kind === "unbuilt";
  const suggested = q.suggested ? `<button class="btn compact" data-act="suggested" title="Byt till den typ som provfilen tyder på">${g("replace", "sm")}Gör om till ${KINDS[q.suggested]}</button>` : "";
  const more = `<button class="btn icon ghost" data-act="more" aria-haspopup="menu" aria-expanded="false" title="Fler åtgärder" aria-label="Fler åtgärder">${g("ellipsis-vertical")}</button>`;
  let html = `<div class="in"><div class="qhead"><h1 class="qnum">Fråga ${lab}</h1>
    <button class="typebtn${unbuilt ? " err" : ""}" data-act="type" aria-haspopup="menu" aria-expanded="false" title="Byt frågetyp" ${q.converting ? "disabled" : ""}>${unbuilt ? g("circle-alert", "sm") : ""}${kindName(q)}${g("chevron-down", "sm")}</button>
    <div class="qtools">${suggested}<span class="phone-hide" style="display:contents">${qtoolsHtml(q, true)}</span>${more}</div></div>`;
  if (unbuilt) html += `<p class="errline" style="margin:-8px 0 12px">${g("circle-alert", "sm")}Frågan kunde inte konverteras och visas som i provfilen. Välj typ eller markera den som granskad.</p>`;
  html += importBox(q, lab);
  if (q.converting) html += `<div class="notice">${g("loader-circle", "sm spin")}<span>Frågan konverteras fortfarande. Texten från provfilen visas tills den är klar och går inte att ändra under tiden.</span></div>`;
  if (parent) {
    const pl = entry(parent.id).lab;
    html += `<div class="pref"><button class="pref-head" data-act="pref" aria-expanded="${S.prefOpen}">${g("book-open", "sm")}<span>Instruktion till fråga ${pl}</span><span class="ex">${esc(parent.text)}</span>${g(S.prefOpen ? "chevron-up" : "chevron-down", "sm")}</button>
      ${S.prefOpen ? `<div class="pref-body">${esc(parent.text)}<br><button class="btn compact" data-goto="${parent.id}">Redigera instruktionen</button></div>` : ""}</div>`;
  }
  html += `<div class="label"${parent ? "" : ' style="margin-top:0"'}>Frågetext</div>
    <div class="rich">${q.converting ? "" : marks()}<div class="ed" ${q.converting ? "" : 'contenteditable="true"'} spellcheck="false" data-field="stem" ${lock}>${stemHtml(q)}</div></div>`;
  html += answerHtml(q);
  html += pointsHtml(q);
  ed.innerHTML = html + "</div>";
}
function keyLine(q) {
  if (!q.facit) return "";
  if (q.keySrc === "ai") return `<div class="keyline">${g("sparkles", "sm ai")}<span class="grow">Facit tolkat av AI ur <q>${esc(q.facit)}</q></span><button class="btn compact" data-act="undo-ai" title="Ångra AI-tolkningen och lämna frågan utan facit">${g("undo-2", "sm")}Ångra AI-tolkningen</button></div>`;
  if (q.keySrc === null && q.facit) return `<div class="keyline">${g("file-text", "sm")}<span class="grow">Facit i provfilen: <q>${esc(q.facit)}</q></span></div>`;
  return `<div class="keyline">${g("file-text", "sm")}<span class="grow">Facit ur provfilen: <q>${esc(q.facit)}</q></span></div>`;
}
function answerHtml(q) {
  if (q.converting || q.kind === "unbuilt") return "";
  if (q.kind === "ett" || q.kind === "flera") {
    const multi = q.kind === "flera";
    const isKey = (i) => multi ? (q.key ?? []).includes(i) : q.key === i;
    const t = q.busy ? "Föreslår facit …" : q.stale ? "Alternativen har ändrats – föreslå facit igen" : q.sugg !== undefined && q.sugg !== null ? "Föreslå facit igen" : "Föreslå facit för den här frågan";
    return `<div class="label"><span class="grow">Alternativ</span><button class="btn icon compact" data-act="ai-one" title="${t}" aria-label="${t}" ${q.busy ? "disabled" : ""} style="width:32px;height:32px">${g(q.busy ? "loader-circle" : "sparkles", `sm${q.busy ? " spin" : ""}`)}${q.stale && !q.busy ? '<span class="badge-dot" style="top:3px;right:3px"></span>' : ""}</button></div>
      <div class="opts" role="${multi ? "group" : "radiogroup"}" aria-label="Facit">${q.opts.map((o, i) => {
        const on = isKey(i), mark = q.sugg === i;
        return `<div class="opt${on ? " on" : ""}" data-o="${i}" role="${multi ? "checkbox" : "radio"}" aria-checked="${on}" title="${multi ? "Markera som rätt svar" : "Välj som rätt svar"}">
          <span class="${multi ? "check" : "radio"}${on ? " on" : ""}"></span><span class="letter">${"ABCDEFGH"[i]}</span>
          <span class="otext" contenteditable="true" spellcheck="false" data-ofield="${i}" aria-label="Text för svarsalternativ ${"ABCDEFGH"[i]}">${esc(o)}</span>
          <span class="aislot">${mark ? `<button class="aimark" data-use-ai aria-pressed="${on}" title="${on ? "AI:s förslag" : "Använd AI:s förslag"}" aria-label="${on ? "AI:s förslag" : "Använd AI:s förslag"}">${g("sparkles", "sm")}</button>` : ""}</span>
          <button class="rm" data-o-del="${i}" title="Ta bort alternativet" aria-label="Ta bort alternativ ${"ABCDEFGH"[i]}" ${q.opts.length <= 2 ? "disabled" : ""}>${g("x", "sm")}</button></div>`;
      }).join("")}</div>
      ${q.opts.some((o) => !o.trim()) ? `<p class="errline">${g("circle-alert", "sm")}Ett svarsalternativ saknar text.</p>` : ""}
      <div class="addrow"><button class="btn compact" data-act="add-opt">${g("plus", "sm")}Alternativ</button></div>${keyLine(q)}`;
  }
  if (q.kind === "lucktext") {
    const partial = q.gaps.some((x) => !x.ans.length) && q.gaps.some((x) => x.ans.length);
    return `${partial ? `<p class="errline">${g("circle-alert", "sm")}Fyll i godkända svar för varje lucka, eller lämna alla luckor tomma om frågan ska sakna facit.</p>` : ""}
      <div class="addrow"><button class="btn compact" data-act="add-gap" title="Lägg till en lucka sist i frågetexten">${g("plus", "sm")}Lucka</button></div>${keyLine(q)}`;
  }
  if (q.kind === "rullista") {
    return `<div class="label">Rullistor</div>${q.rgaps.map((r, gi) => `<div class="rgap${S.curGap === gi ? " cur" : ""}" data-rgap="${gi}"><div class="rgap-h">Lucka ${gi + 1}<span class="muted">${r.opts.length} alternativ</span></div>
      <div class="opts" role="radiogroup" aria-label="Rätt svar i lucka ${gi + 1}">${r.opts.map((o, i) => `<div class="opt${r.key === i ? " on" : ""}" data-ro="${gi}:${i}" role="radio" aria-checked="${r.key === i}" title="Välj som rätt svar">
        <span class="radio${r.key === i ? " on" : ""}"></span><span class="otext" contenteditable="true" spellcheck="false" data-rofield="${gi}:${i}" aria-label="Alternativ ${i + 1} i lucka ${gi + 1}">${esc(o)}</span>
        ${r.key === i ? '<span class="chip teal">Rätt svar</span>' : ""}
        <button class="rm" data-ro-del="${gi}:${i}" title="Ta bort alternativet" aria-label="Ta bort alternativet" ${r.opts.length <= 2 ? "disabled" : ""}>${g("x", "sm")}</button></div>`).join("")}</div>
      ${r.key === null ? `<p class="errline" style="padding:0 12px 8px">${g("circle-alert", "sm")}Välj rätt svar.</p>` : ""}
      <div class="addrow"><button class="btn compact" data-ro-add="${gi}">${g("plus", "sm")}Alternativ</button></div></div>`).join("")}
      <div class="addrow"><button class="btn compact" data-act="add-rgap" title="Lägg till en rullista sist i frågetexten">${g("plus", "sm")}Lucka</button></div>`;
  }
  if (q.kind === "kategorisera") {
    const gr = q.grid;
    return `<div class="label">Kategorisera</div><table class="grid"><thead><tr><th><span class="muted" style="font-weight:400">Rad</span></th>${gr.cats.map((c, ci) => `<th><span contenteditable="true" data-cat="${ci}" aria-label="Text för kategori ${ci + 1}">${esc(c)}</span></th>`).join("")}</tr></thead>
      <tbody>${gr.rows.map((r, ri) => `<tr><td><span contenteditable="true" data-grow="${ri}" aria-label="Text för rad ${ri + 1}">${esc(r)}</span></td>${gr.cats.map((c, ci) => `<td><span class="check${gr.ticks[ri][ci] ? " on" : ""}" role="checkbox" aria-checked="${!!gr.ticks[ri][ci]}" aria-label="${esc(r)}: ${esc(c)}" data-tick="${ri}:${ci}" tabindex="0"></span></td>`).join("")}</tr>`).join("")}</tbody></table>
      ${gr.cats.some((c) => !c.trim()) || gr.rows.some((r) => !r.trim()) ? `<p class="errline">${g("circle-alert", "sm")}En rad eller en kategori saknar text.</p>` : ""}
      <div class="addrow" style="display:flex;gap:8px"><button class="btn compact" data-act="add-row">${g("plus", "sm")}Rad</button><button class="btn compact" data-act="add-cat">${g("plus", "sm")}Kategori</button></div>`;
  }
  // fritext
  return `<div class="label"><span class="grow">Bedömningskriterier</span></div>
    ${(q.crit ?? []).map((c, i) => `<div class="crit"><input class="input" data-crit-t="${i}" value="${esc(c[0])}" aria-label="Kriterium ${i + 1}" placeholder="Kriterium" />
      <input class="input" data-crit-p="${i}" type="number" min="1" step="1" value="${c[1]}" aria-label="Poäng för kriterium ${i + 1}" />
      <button class="rm" data-crit-del="${i}" title="Ta bort kriterium ${i + 1}" aria-label="Ta bort kriterium ${i + 1}">${g("trash-2", "sm")}</button></div>`).join("")}
    <div class="addrow"><button class="btn compact" data-act="add-crit" aria-label="Lägg till kriterium">${g("plus", "sm")}Kriterium</button></div>`;
}
function pointsHtml(q) {
  if (q.converting) return `<div class="ptsrow"><label class="label">Poäng</label><input class="input" value="${q.points ?? ""}" disabled /></div>`;
  const p = pts(q), missing = p === null || p === undefined;
  if (q.kind === "kategorisera") return `<div class="ptsrow"><label class="label" for="tick">Poäng per kryss</label><input class="input" id="tick" data-field="tick" type="number" min="0.01" step="0.01" value="${q.tick}" />
    <label class="label">Poäng</label><input class="input" value="${p}" readonly title="Poäng per kryss × antal kryss" /></div>`;
  if (q.kind === "fritext" && q.crit?.length) return `<div class="ptsrow"><label class="label">Poäng</label><input class="input" value="${p}" readonly title="Summan av kriteriernas poäng" /></div>`;
  return `<div class="ptsrow"><label class="label" for="pts">Poäng</label><input class="input" id="pts" data-field="points" type="number" min="0" inputmode="decimal" value="${missing ? "" : p}" aria-invalid="${missing}" aria-describedby="pts-msg" />
    ${missing ? `<span class="errline" id="pts-msg" style="margin:0">${g("circle-alert", "sm")}Saknas</span>` : q.est ? `<span class="hint" id="pts-msg" style="margin:0">${g("info", "sm")}Uppskattad utifrån avsnittets totalpoäng</span>` : ""}</div>`;
}

// ───────── Change type: text and points carry over; dropped content is named; one undo restores ─────────
function changeType(q, kind) {
  if (q.kind === kind) return;
  step();
  const dropped = [];
  const n = (k, one, many) => (k === 1 ? one : `${k} ${many}`);
  if (q.opts?.length && kind !== "ett" && kind !== "flera") { dropped.push(n(q.opts.length, "1 svarsalternativ", "svarsalternativ")); if (q.key !== null && q.key !== undefined) dropped.push("facit"); }
  if (q.gaps?.length && kind !== "lucktext") dropped.push(q.gaps.length === 1 ? "luckan och dess svar" : `${q.gaps.length} luckor och deras svar`);
  if (q.rgaps?.length && kind !== "rullista") dropped.push(q.rgaps.length === 1 ? "rullistan" : `${q.rgaps.length} rullistor`);
  if (q.grid && kind !== "kategorisera") dropped.push("kategorier, rader och kryss");
  if (q.crit?.length && kind !== "fritext") dropped.push(n(q.crit.length, "1 bedömningskriterium", "bedömningskriterier"));
  const p = pts(q);
  q.stem = q.stem.replace(/\s*\{\d+\}/g, " ___").trim();
  const was = q.kind;
  for (const k of ["opts", "key", "gaps", "rgaps", "grid", "crit", "sugg", "stale", "tick"]) if (!(k === "opts" && (kind === "ett" || kind === "flera") && (was === "ett" || was === "flera"))) delete q[k];
  if (was === "ett" && kind === "flera" && q.key !== undefined) q.key = q.key === null ? [] : [q.key];
  if (was === "flera" && kind === "ett") q.key = null;
  q.kind = kind; q.points = p ?? null; q.ok = false;
  if (kind === "ett" || kind === "flera") { q.opts ??= ["", ""]; q.key ??= kind === "flera" ? [] : null; q.keySrc = null; }
  if (kind === "lucktext") { q.stem = `${q.stem.replace(/ ___/, " {1}")}${q.stem.includes("{1}") || / ___/.test(q.stem) ? "" : " {1}"}`.replace(/ ___/g, ""); q.gaps = [{ ans: [], auto: [] }]; q.keySrc = null; }
  if (kind === "rullista") { q.stem = `${q.stem.replace(/ ___/, " {1}")}${q.stem.includes("{1}") || / ___/.test(q.stem) ? "" : " {1}"}`.replace(/ ___/g, ""); q.rgaps = [{ opts: ["", ""], key: null }]; q.keySrc = null; }
  if (kind === "kategorisera") { q.grid = { cats: [""], rows: [""], ticks: [[0]] }; q.tick = p ?? 1; q.keySrc = null; }
  if (kind === "fritext") { q.crit = []; q.keySrc = null; }
  if (q.suggested === kind) delete q.suggested;
  S.impOpen = false; render();
  toast(`Bytte till ${KINDS[kind]}.${dropped.length ? ` Borttaget: ${listSv(dropped)}.` : ""}`, { glyph: "replace", action: ["Ångra", undo, "undo-2"], sticky: true });
}
const listSv = (a) => (a.length < 2 ? a.join("") : `${a.slice(0, -1).join(", ")} och ${a[a.length - 1]}`);

// ───────── New items, parents and children ─────────
function newQ(kind) {
  const q = { k: "q", id: `n${Date.now()}${Math.random().toString(36).slice(2, 5)}`, kind: kind === "kortsvar" ? "lucktext" : kind, stem: "Ny fråga", points: null, ok: false, keySrc: null };
  if (kind === "ett" || kind === "flera") { q.opts = ["", ""]; q.key = kind === "flera" ? [] : null; }
  if (kind === "lucktext" || kind === "kortsvar") { q.stem = "Ny fråga {1}"; q.gaps = [{ ans: [], auto: [] }]; }
  if (kind === "rullista") { q.stem = "Ny fråga {1}"; q.rgaps = [{ opts: ["", ""], key: null }]; }
  if (kind === "kategorisera") { q.grid = { cats: ["", ""], rows: [""], ticks: [[0, 0]] }; q.tick = 1; }
  if (kind === "fritext") q.crit = [];
  return q;
}
function topIndexOfSel() { const e = entry(S.sel); const top = e?.parent ?? e?.it; return S.exam.items.indexOf(top); }
function addItem(kind) {
  step();
  const at = topIndexOfSel() + 1;
  let it;
  if (kind === "instruktion") { it = { k: "p", id: `p${Date.now()}`, text: "Ny instruktion", kids: [newQ("fritext")] }; }
  else it = newQ(kind);
  S.exam.items.splice(at, 0, it); S.sel = it.id; S.impOpen = false; render();
  document.querySelector(".row.sel")?.scrollIntoView({ block: "nearest" });
}
function addChild(kind) {
  const e = entry(S.sel); const p = e.it.k === "p" ? e.it : e.parent; if (!p) return;
  step(); const q = newQ(kind); p.kids.push(q); S.sel = q.id; render();
}
function moveKid(p, j, d) { step(); const k = p.kids.splice(j, 1)[0]; p.kids.splice(j + d, 0, k); render(); }
function delKid(p, j) { if (p.kids.length === 1) return; step(); p.kids.splice(j, 1); render(); toast("Deluppgiften är borttagen.", { action: ["Ångra", undo, "undo-2"] }); }
function delTop(it) { step(); const i = S.exam.items.indexOf(it); S.exam.items.splice(i, 1); S.sel = (S.exam.items[i] ?? S.exam.items[i - 1])?.id; render(); toast("Frågan är borttagen.", { action: ["Ångra", undo, "undo-2"] }); }

// ───────── Drawers ─────────
function setDrawer(name) {
  S.drawer = S.drawer === name ? null : name;
  for (const [n, id] of [["open", "d-open"], ["export", "d-export"], ["meta", "d-meta"]]) $(id).hidden = S.drawer !== n;
  $("body").classList.toggle("with-drawer", !!S.drawer);
  closeMenus(); renderDrawers(); renderHeader();
}
function renderDrawers() {
  if (S.drawer === "open") renderOpen();
  if (S.drawer === "export") renderExport();
  if (S.drawer === "meta") renderMeta();
}
function courseCombo(id, value) {
  const c = course(value);
  return `<div class="combo"><input class="input" id="${id}" data-combo="${id}" role="combobox" aria-expanded="false" aria-controls="m-course" aria-label="Kurs" placeholder="Sök kurs eller kurskod" value="${c ? esc(`${c.name} · ${c.key}`) : ""}" ${id === "imp-course" && dirty() ? "disabled" : ""} />
    ${c ? `<button class="btn icon ghost compact cx" data-clear-course="${id}" title="Rensa kurs" aria-label="Rensa kurs">${g("x", "sm")}</button>` : ""}</div>`;
}
let importCourse = "SVESVE02";
function renderOpen() {
  const blocked = dirty() || !!S.importing;
  const intake = S.importing ? `<div class="prog"><div style="display:flex;gap:8px;align-items:center">${g("loader-circle", "sm spin")}<b style="font-weight:500">Kursprov Engelska 6.docx</b></div>
      <div>${S.importing.done ? `Konverterar provet: ${S.importing.done} av ${S.importing.total} frågor klara.` : "Konverterar provet …"}</div>
      <div class="bar" role="progressbar" aria-label="Konverterade frågor" aria-valuemin="0" aria-valuemax="${S.importing.total}" aria-valuenow="${S.importing.done}"><i style="width:${(100 * S.importing.done) / S.importing.total}%"></i></div>
      ${S.importing.done ? '<small class="muted" style="font-size:12px">Klara frågor går att redigera direkt.</small>' : ""}</div>`
    : `<div class="drop${blocked ? " off" : ""}" id="drop">${g("file-up", "lg")}<b style="font-weight:600;font-size:14px">Provfil</b>
      <div class="fmt"><span class="chip">Word .docx</span><span class="chip">DigiExam .dxe</span></div>
      <button class="btn" data-act="pick" ${blocked ? "disabled" : ""}>${g("upload")}Välj provfil</button><small>eller dra hit filen</small></div>`;
  const groups = groupExams();
  $("open-body").innerHTML = `<div class="sect"><h3>Importera prov</h3>
      <label class="label" style="margin-top:0" for="imp-course">Kurs (valfritt)</label>${courseCombo("imp-course", importCourse)}
      <div style="height:12px"></div>${intake}
      ${dirty() ? `<p class="hint">${g("info", "sm")}Spara det öppna provet innan du importerar eller öppnar ett annat.</p>` : ""}</div>
    <div class="sect"><h3><span class="grow">Prov</span><span class="seg" role="group" aria-label="Ordning">
      <button aria-pressed="${S.sort === "kurs"}" data-sort="kurs">Per kurs</button><button aria-pressed="${S.sort === "senaste"}" data-sort="senaste">Senaste</button></span></h3>
      ${groups.map(([h, code, list]) => `<div class="egroup">${h ? `<h4>${h}${code ? `<span class="code">${code}</span>` : ""}</h4>` : ""}<div class="files">${list.map(fileRow).join("")}</div></div>`).join("")}</div>`;
}
function groupExams() {
  const list = [...EXAMS].sort((a, b) => b.t - a.t);
  if (S.sort === "senaste") return [[null, null, list]];
  const mine = COURSES.filter((c) => c.mine).map((c) => c.key);
  const keys = [...new Set(list.map((x) => x.course).filter(Boolean))].sort((a, b) => {
    const ia = mine.indexOf(a), ib = mine.indexOf(b);
    if (ia !== -1 || ib !== -1) return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    return course(a).name.localeCompare(course(b).name, "sv");
  });
  const out = keys.map((k) => [course(k).name, k, list.filter((x) => x.course === k)]);
  const none = list.filter((x) => !x.course); if (none.length) out.push(["Utan kurs", null, none]);
  return out;
}
function fileRow(x) {
  const cur = S.exam?.id === x.id, off = !cur && dirty();
  const ex = Object.entries(x.exports).map(([f, t]) => `<span class="chip" title="${f} i Mina filer, sparad ${t}">${g("folder-input")}${f}</span>`).join("");
  const notes = cur ? S.exam.notes ?? [] : x.notes ?? [];
  return `<div class="file${cur ? " cur" : ""}" data-open-exam="${x.id}" role="button" tabindex="0" ${off ? 'aria-disabled="true" title="Spara det öppna provet innan du öppnar ett annat."' : ""}>${g("file-text", "sm")}
    <span style="min-width:0"><div class="t">${esc(x.title)}</div><div class="m">Sparad ${x.saved}${x.origin === "digiexam" ? '<span class="chip">DigiExam</span>' : ""}${ex}</div>
    ${notes.length ? `<ul class="notes">${notes.map((n) => `<li>${g("info", "sm")}<span>${esc(n)}</span></li>`).join("")}</ul>` : ""}</span>${cur ? '<span class="tag">Öppet</span>' : "<span></span>"}</div>`;
}
function renderExport() {
  const blocked = exportBlockers();
  const r = examRow(), had = r?.exports[S.fmt];
  $("export-body").innerHTML = `${blocked.length ? blockHtml(blocked) : ""}
    <div class="sect"><h3>Format</h3><div class="seg lg" role="group" aria-label="Format">${["QTI", "PDF", "DOCX"].map((f) => `<button aria-pressed="${S.fmt === f}" data-fmt-sel="${f}">${f}</button>`).join("")}</div>
      <p class="hint">${{ QTI: "För import i Exam.net", PDF: "För utskrift", DOCX: "För redigering i Word" }[S.fmt]}</p></div>
    <div class="sect"><h3>Filnamn</h3><input class="input" value="${esc(fileName(S.exam.title, S.fmt))}" aria-label="Filnamn" /></div>
    <div class="sect"><h3>Mål</h3>
      <label class="choice"><input type="radio" name="dest" value="download" ${S.dest === "download" ? "checked" : ""}/> <span>Ladda ner</span></label>
      <label class="choice"><input type="radio" name="dest" value="files" ${S.dest === "files" ? "checked" : ""}/> <span>Spara i Mina filer<small>${had ? `Ersätter ${S.fmt}-filen från ${had}` : "Visas under provet i Mina filer"}</small></span></label></div>
    <div class="sect"><button class="btn" data-act="do-export" ${blocked.length ? "disabled" : ""}>${g(S.dest === "files" ? "folder-input" : "download")}${S.dest === "files" ? "Spara i Mina filer" : "Ladda ner"}</button></div>
    ${S.checklist ? `<div class="sect" id="checklist"><h3>${g("list-checks", "sm")}Det här tappar Exam.net vid import</h3><div class="checklist">${CHECKLIST.map(([n, t, x]) => `<div class="xl"><b>Fråga ${n}: ${esc(t)}</b><span>${esc(x)}</span></div>`).join("")}</div></div>` : ""}`;
}
function exportBlockers() {
  if (!S.exam) return [];
  return qs().flatMap(({ it, lab }) => blockers(it).map((b) => [it.id, lab, b]));
}
const blockHtml = (b) => `<div class="mblock"><b>${g("octagon-alert", "sm")}Kan inte exporteras ännu</b>${b.map(([id, lab, why]) => `<button data-goto="${id}">Fråga ${lab}: ${why}</button>`).join("")}</div>`;
function doExport(f, dest) {
  closeMenus();
  if (exportBlockers().length) return;
  const r = examRow();
  if (dest === "files") { const replaced = r.exports[f]; r.exports[f] = `17 okt ${now()}`; toast(`${f} sparad i Mina filer${replaced ? ` och ersatte filen från ${replaced}` : ""}.`, { glyph: "folder-input" }); }
  else toast({ QTI: "QTI-paketet är skapat.", PDF: "PDF-filen är skapad.", DOCX: "Word-filen är skapad." }[f], { glyph: "download" });
  if (f === "QTI") { S.checklist = true; setTimeout(() => toast(`${dest === "files" ? "QTI sparad i Mina filer." : "QTI-paketet är skapat."} Exam.net tappar en del vid import.`, { glyph: "list-checks", action: ["Visa listan", () => { if (S.drawer !== "export") setDrawer("export"); else renderExport(); $("checklist")?.scrollIntoView(); }], sticky: true }), 50); }
  renderDrawers();
}
function renderMeta() {
  const c = course(S.exam.course);
  const content = c ? CONTENT[c.key] : null;
  $("meta-body").innerHTML = `<div class="sect"><h3>Titel</h3><input class="input" data-field="title" value="${esc(S.exam.title)}" aria-label="Titel" /></div>
    <div class="sect"><h3>Filnamn i Mina filer</h3><div style="display:flex;gap:8px"><input class="input" value="${esc(S.exam.file)}" aria-label="Filnamn i Mina filer" /><button class="btn" data-act="rename">Byt namn</button></div></div>
    <div class="sect"><h3>Kurs</h3>${courseCombo("meta-course", S.exam.course)}
      <div class="coursefoot">${c ? (c.mine ? `<span class="okline">${g("check", "sm")}I mina kurser</span>` : `<button class="linkbtn" data-act="addcourse">${g("plus", "sm")}Lägg till i mina kurser</button>`) : ""}
      ${c && c.form.startsWith("Gymnasiet") ? `<span class="okline">Ämne: ${c.name.replace(/ \d+$/, "")}</span>` : ""}</div>
      ${!c && S.exam.courseHint ? `<p class="hint">${g("file-text", "sm")}Kursrad i dokumentet: ${esc(S.exam.courseHint)}</p>` : ""}</div>
    <div class="sect"><h3><span class="grow">Centralt innehåll</span><button class="btn compact" data-act="suggest-tags" ${!c || S.tagsBusy ? "disabled" : ""}>${g(S.tagsBusy ? "loader-circle" : "sparkles", `sm${S.tagsBusy ? " spin" : ""}`)}Föreslå innehåll</button></h3>
      ${content ? `<div class="checklist" role="group" aria-label="Centralt innehåll"${S.tagsBusy ? ' style="opacity:.5"' : ""}>${content.map((t, i) => {
        const on = S.exam.tags.includes(i);
        return `<div class="cl" data-tag="${i}" role="checkbox" aria-checked="${on}" tabindex="0"><span class="check${on ? " on" : ""}"></span><span>${esc(t.t)}${t.cites.length ? `<span class="cites">${t.sugg ? g("sparkles", "sm ai") : ""}Fråga ${t.cites.join(", ")}</span>` : ""}</span></div>`;
      }).join("")}</div>` : `<p class="hint">${g("info", "sm")}Välj en kurs för att se kursens centrala innehåll.</p>`}</div>`;
}
function openCourseMenu(input) {
  const q = (S.courseQuery ?? "").toLowerCase();
  const match = (c) => !q || `${c.name} ${c.key}`.toLowerCase().includes(q);
  const mine = COURSES.filter((c) => c.mine && match(c)), rest = COURSES.filter((c) => !c.mine && match(c));
  const opt = (c) => `<button class="mi" role="option" data-pick-course="${c.key}" data-for="${input.id}"><span class="stack"><span class="grow">${c.name}</span><small>${c.key} · ${c.form}</small></span></button>`;
  const m = $("m-course");
  m.innerHTML = (mine.length ? `<div class="mhead">Mina kurser</div>${mine.map(opt).join("")}` : "") + (rest.length ? `<div class="mhead">Alla kurser</div>${rest.map(opt).join("")}` : "")
    + (!mine.length && !rest.length ? '<div class="mhead">Inga kurser hittades.</div>' : "");
  place(m, input, "left", input.getBoundingClientRect().width); input.setAttribute("aria-expanded", "true");
}
function pickCourse(id, key) {
  closeMenus(); S.courseQuery = null;
  if (id === "imp-course") { importCourse = key; renderOpen(); return; }
  step(); S.exam.course = key; S.exam.tags = []; render();
  if (key) { S.tagsBusy = true; renderMeta(); setTimeout(() => { S.tagsBusy = false; if (CONTENT[key]) S.exam.tags = CONTENT[key].map((t, i) => (t.sugg ? i : -1)).filter((i) => i >= 0); renderMeta(); }, 1200); }
}

// ───────── Menus ─────────
function place(m, anchor, align = "right", width) {
  m.hidden = false; const r = anchor.getBoundingClientRect();
  if (width) m.style.width = `${Math.max(width, 260)}px`; else m.style.width = "";
  const w = m.offsetWidth;
  m.style.top = `${Math.min(r.bottom + 6, innerHeight - Math.min(m.scrollHeight, innerHeight - 80) - 8)}px`;
  m.style.left = `${align === "right" ? Math.max(12, r.right - w) : Math.min(r.left, innerWidth - w - 12)}px`;
  anchor.setAttribute("aria-expanded", "true"); S.anchor = anchor;
}
function closeMenus() {
  for (const id of ["m-export", "m-save", "m-new", "m-type", "m-more", "m-course"]) $(id).hidden = true;
  document.querySelectorAll('[aria-expanded="true"][aria-haspopup="menu"], [data-combo][aria-expanded="true"]').forEach((b) => b.setAttribute("aria-expanded", "false"));
  closeGap();
}
function openExportMenu() {
  const blocked = exportBlockers(), r = examRow();
  $("m-export").innerHTML = `${blocked.length ? blockHtml(blocked) : ""}${[["QTI", "Exam.net"], ["PDF", "utskrift"], ["DOCX", "Word"]].map(([f, sub]) => `<div class="mi" role="menuitem" data-fmt="${f}" ${blocked.length ? 'aria-disabled="true"' : ""} tabindex="0" title="Ladda ner ${f}">
      ${g("download")}<span class="stack"><span class="grow">${f} <span class="sub">${sub}</span></span>${r?.exports[f] ? `<small>${g("folder-input", "sm")}I Mina filer ${r.exports[f]}</small>` : ""}</span>
      <button class="mini" data-save-fmt="${f}" title="Spara ${f} i Mina filer${r?.exports[f] ? ` (ersätter filen från ${r.exports[f]})` : ""}" aria-label="Spara ${f} i Mina filer" ${blocked.length ? "disabled" : ""}>${g("folder-input")}</button></div>`).join("")}
    <div class="mdiv"></div><button class="mi" data-act="more-export" role="menuitem"><span style="width:20px"></span><span class="grow">Fler val …</span></button>`;
  place($("m-export"), $("b-export"), phoneMq.matches ? "left" : "right");
}
// Ordning has a reserved place in Byt frågetyp and Ny uppgift until TASK-SKRIPT-39-06-02 decides whether it is built
// (user 2026-10-17); ordering questions are standalone only (ST-SKRIPT-39-06 P3), so menus for deluppgifter omit it.
const ordningItem = (hintId) => `<button class="mi" role="menuitem" aria-disabled="true" tabindex="-1" aria-describedby="${hintId}" data-reserved="ordning"><span style="width:20px"></span><span class="grow">Ordning</span><span class="hint" id="${hintId}">Kommer senare</span></button>`;
function typeMenu(anchor, q) {
  $("m-type").innerHTML = `<div class="mhead">Byt frågetyp</div>${Object.entries(KINDS).map(([k, v]) => `<button class="mi" role="menuitemradio" aria-checked="${q.kind === k}" data-kind="${k}">${q.kind === k ? g("check") : '<span style="width:20px"></span>'}<span class="grow">${v}</span>${q.suggested === k ? `<span class="chip teal">${g("replace")}Förslag</span>` : ""}</button>`).join("")}${entry(q.id)?.parent ? "" : ordningItem("hint-ordning-type")}`;
  place($("m-type"), anchor, "left");
}
function newMenu(anchor, child) {
  $("m-new").innerHTML = `<div class="mhead">${child ? "Ny deluppgift" : "Ny fråga"}</div>${NEW_ITEMS.map(([k, v]) => `<button class="mi" role="menuitem" data-new="${k}" data-child="${child ? 1 : 0}"><span style="width:20px"></span><span class="grow">${v}</span></button>`).join("")}${child ? "" : ordningItem("hint-ordning-new")}
    ${child ? "" : `<div class="mdiv"></div><button class="mi" role="menuitem" data-new="instruktion" data-child="0">${g("book-open")}<span class="grow">Instruktion med deluppgifter</span></button>`}`;
  place($("m-new"), anchor, child ? "right" : "right");
}
function moreMenu(anchor) {
  const e = entry(S.sel);
  if (e.parent) {
    const j = e.parent.kids.indexOf(e.it), n = e.parent.kids.length;
    $("m-more").innerHTML = `<button class="mi" data-more="up" ${j === 0 ? 'aria-disabled="true"' : ""}>${g("arrow-up")}<span class="grow">Flytta upp</span></button>
      <button class="mi" data-more="down" ${j === n - 1 ? 'aria-disabled="true"' : ""}>${g("arrow-down")}<span class="grow">Flytta ned</span></button><div class="mdiv"></div>
      <button class="mi" data-more="del" ${n === 1 ? 'aria-disabled="true" title="En instruktion behöver minst en deluppgift"' : ""}>${g("trash-2")}<span class="grow">Ta bort deluppgiften</span></button>`;
  } else $("m-more").innerHTML = `<button class="mi" data-more="del">${g("trash-2")}<span class="grow">Ta bort frågan</span></button>`;
  place($("m-more"), anchor, "right");
}

// ───────── Gap popover (typed Lucktext) ─────────
function openGap(chip) {
  const q = entry(S.sel).it, i = +chip.dataset.gap;
  if (q.kind === "rullista") { S.curGap = i; renderEditor(); document.querySelector(`[data-rgap="${i}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" }); return; }
  S.gapPop = i; const x = q.gaps[i];
  const last = q.gaps.length === 1, empty = !x.ans.length;
  const p = $("gap-pop");
  p.innerHTML = `<h3><span class="grow">Godkända svar för lucka ${i + 1}</span><button class="btn icon ghost compact" data-act="gap-close" aria-label="Stäng" title="Stäng">${g("x", "sm")}</button></h3>
    <label class="label" style="margin:0" for="gap-in">Godkända svar (kommaseparerade)</label><input class="input" id="gap-in" value="${esc(x.ans.join(", "))}" />
    ${x.auto.length ? `<div class="label" style="margin:4px 0 0">Automatiska svar</div><div class="chips">${x.auto.map((a, k) => `<span class="chip">${esc(a)} <i>automatisk</i><button class="x" data-auto-del="${k}" title="Ta bort automatisk stavning: ${esc(a)}" aria-label="Ta bort automatisk stavning: ${esc(a)}">${g("x")}</button></span>`).join("")}</div>` : ""}
    <div class="foot"><button class="btn compact" data-act="gap-text" ${last || empty ? "disabled" : ""}>Visa som text</button>
      ${last ? '<span class="hint" style="margin:0">Frågan måste behålla minst en lucka.</span>' : empty ? '<span class="hint" style="margin:0">Fyll i ett godkänt svar först.</span>' : ""}</div>`;
  const r = chip.getBoundingClientRect(); p.hidden = false;
  p.style.top = `${r.bottom + 8}px`; p.style.left = `${Math.max(12, Math.min(r.left, innerWidth - p.offsetWidth - 12))}px`;
  chip.setAttribute("aria-expanded", "true"); $("gap-in").focus();
}
function commitGap() {
  if (S.gapPop === null) return;
  const q = entry(S.sel).it, x = q.gaps[S.gapPop], v = $("gap-in").value.split(",").map((s) => s.trim()).filter(Boolean);
  if (v.join(",") !== x.ans.join(",")) { step(); x.ans = v; }
}
function closeGap() { if (S.gapPop === null) return; S.gapPop = null; $("gap-pop").hidden = true; renderEditor(); renderRows(); }

// ───────── Toast ─────────
let toastTimer;
function toast(text, { glyph = "info", action = null, sticky = false } = {}) {
  $("toast-glyph").innerHTML = `<span class="${glyph === "circle-check" ? "ok" : "ai"}">${g(glyph)}</span>`;
  $("toast-text").textContent = text; $("toast").hidden = false;
  const a = $("toast-action"); a.hidden = !action;
  if (action) { a.innerHTML = `${action[2] ? g(action[2]) : ""}${action[0]}`; a.onclick = (e) => { e.stopPropagation(); hideToast(); action[1](); }; }
  clearTimeout(toastTimer); if (!sticky) toastTimer = setTimeout(hideToast, 4200);
}
function hideToast() { $("toast").hidden = true; }
function checkAllReviewed() {
  if (qs().every(({ it }) => it.ok) && !exportBlockers().length) toast("Alla frågor är granskade", { glyph: "circle-check", action: ["Exportera", openExportMenu, "download"], sticky: true });
}

// ───────── AI answer keys ─────────
function suggestAll(resumed = false) {
  if (S.busyAll) return;
  const targets = qs().filter(({ it }) => (it.kind === "ett" || it.kind === "flera") && (it.key === null || (Array.isArray(it.key) && !it.key.length)));
  if (!targets.length && !resumed) { toast("Alla frågor har facit."); return; }
  S.busyAll = true; renderHeader();
  if (resumed) toast("Facitförslagen tas fram …", { glyph: "loader-circle" });
  setTimeout(() => {
    S.busyAll = false;
    if (targets.length) step();
    targets.forEach(({ it }) => { it.sugg = 0; it.key = it.kind === "flera" ? [0] : 0; it.keySrc = "machine"; it.ok = false; if (!it.opts[0]) it.opts[0] = "Förslag från AI"; });
    render();
    toast(targets.length ? `${targets.length} facitförslag har lagts in på frågorna.` : "Inga facitförslag kom tillbaka. Komplettera facit manuellt.", { glyph: "sparkles" });
  }, resumed ? 2600 : 1400);
}

// ───────── Render ─────────
function render() { renderHeader(); renderRows(); renderEditor(); renderDrawers(); }
function go(id) { closeMenus(); S.sel = id; S.impOpen = false; S.prefOpen = false; S.curGap = null; document.body.classList.remove("show-list"); render(); document.querySelector(".row.sel")?.scrollIntoView({ block: "nearest" }); }
function goStep(d) { const all = entries(); const i = all.findIndex((e) => e.it.id === S.sel); go(all[(i + d + all.length) % all.length].it.id); }
function openExam(id) {
  const x = EXAMS.find((e) => e.id === id); if (!x || (S.exam && dirty() && S.exam.id !== id)) return;
  if (id === "e1") S.exam = makeExam();
  else S.exam = { id, title: x.title, file: x.title, course: x.course, printed: null, origin: x.origin, tags: [], notes: x.notes ?? [], items: [
    { k: "q", id: `${id}q1`, kind: "ett", stem: "Vilket alternativ stämmer bäst med texten?", points: 1, ok: true, keySrc: "source", opts: ["Alternativ A", "Alternativ B", "Alternativ C"], key: 0, imp: { orig: "1. Vilket alternativ stämmer bäst med texten? (1 p)", steps: ["Typ: Flerval: ett val", "Facit: kopierat ur provfilen"] } },
    { k: "q", id: `${id}q2`, kind: "fritext", stem: "Motivera ditt svar med två exempel ur texten.", points: 4, ok: true, keySrc: null, crit: [], imp: { orig: "2. Motivera ditt svar med två exempel ur texten. (4 p)", steps: ["Typ: Fritext"] } }] };
  S.saved = snap(); S.savedAt = x.saved; S.undo = []; S.redo = []; S.sel = qs()[0].it.id; S.checklist = false;
  setView("workspace"); if (S.drawer) setDrawer(S.drawer); render();
}

// ───────── Events ─────────
document.addEventListener("click", (e) => {
  const t = e.target;
  const c = (sel) => t.closest(sel);
  if (!c(".menu") && !c("[aria-haspopup]") && !c("#gap-pop") && !c(".gap") && !c("[data-combo]")) closeMenus();
  let el;
  if ((el = c("[data-nav]"))) { const v = el.dataset.nav; setView(v === "workspace" ? "workspace" : v); return; }
  if ((el = c("[data-open-exam]"))) { if (el.getAttribute("aria-disabled") !== "true") openExam(el.dataset.openExam); return; }
  if ((el = c("[data-goto]"))) { closeMenus(); go(el.dataset.goto); return; }
  if ((el = c(".row"))) { go(el.dataset.id); return; }
  if ((el = c("[data-mark]"))) { e.preventDefault(); const m = el.dataset.mark; document.execCommand(m.startsWith("h") ? "formatBlock" : m, false, m.startsWith("h") ? m.replace("h", "h") : null); return; }
  if ((el = c(".gap"))) { e.preventDefault(); openGap(el); return; }
  if ((el = c("[data-use-ai]"))) { const q = entry(S.sel).it; step(); q.key = q.kind === "flera" ? [q.sugg] : q.sugg; renderEditor(); return; }
  if ((el = c("[data-o-del]"))) { const q = entry(S.sel).it, i = +el.dataset.oDel; step(); q.opts.splice(i, 1); if (q.kind === "flera") q.key = q.key.filter((k) => k !== i).map((k) => (k > i ? k - 1 : k)); else q.key = q.key === i ? null : q.key > i ? q.key - 1 : q.key; render(); return; }
  if ((el = c("[data-o]")) && !c(".otext")) { const q = entry(S.sel).it, i = +el.dataset.o; step();
    if (q.kind === "flera") q.key = q.key.includes(i) ? q.key.filter((k) => k !== i) : [...q.key, i].sort(); else q.key = i;
    if (q.keySrc === "ai") q.keySrc = "source"; renderEditor(); renderRows(); return; }
  if ((el = c("[data-ro-del]"))) { const [gi, i] = el.dataset.roDel.split(":").map(Number); const r = entry(S.sel).it.rgaps[gi]; step(); r.opts.splice(i, 1); r.key = r.key === i ? null : r.key > i ? r.key - 1 : r.key; render(); return; }
  if ((el = c("[data-ro]")) && !c(".otext")) { const [gi, i] = el.dataset.ro.split(":").map(Number); step(); entry(S.sel).it.rgaps[gi].key = i; S.curGap = gi; render(); return; }
  if ((el = c("[data-ro-add]"))) { step(); entry(S.sel).it.rgaps[+el.dataset.roAdd].opts.push(""); render(); document.querySelectorAll(`[data-rofield^="${el.dataset.roAdd}:"]`).forEach((n, k, a) => k === a.length - 1 && n.focus()); return; }
  if ((el = c("[data-tick]"))) { const [ri, ci] = el.dataset.tick.split(":").map(Number); const q = entry(S.sel).it; step(); q.grid.ticks[ri][ci] = q.grid.ticks[ri][ci] ? 0 : 1; render(); return; }
  if ((el = c("[data-crit-del]"))) { step(); entry(S.sel).it.crit.splice(+el.dataset.critDel, 1); render(); return; }
  if ((el = c("[data-kid-up]"))) { moveKid(entry(S.sel).it, +el.dataset.kidUp, -1); return; }
  if ((el = c("[data-kid-down]"))) { moveKid(entry(S.sel).it, +el.dataset.kidDown, 1); return; }
  if ((el = c("[data-kid-del]"))) { delKid(entry(S.sel).it, +el.dataset.kidDel); return; }
  if ((el = c("[data-kind]"))) { closeMenus(); changeType(entry(S.sel).it, el.dataset.kind); return; }
  if ((el = c("[data-new]"))) { closeMenus(); el.dataset.child === "1" ? addChild(el.dataset.new) : addItem(el.dataset.new); return; }
  if ((el = c("[data-more]"))) { if (el.getAttribute("aria-disabled") === "true") return; closeMenus(); const en = entry(S.sel);
    if (en.parent) { const j = en.parent.kids.indexOf(en.it); if (el.dataset.more === "del") delKid(en.parent, j); else moveKid(en.parent, j, el.dataset.more === "up" ? -1 : 1); }
    else delTop(en.it); return; }
  if ((el = c("[data-save-fmt]"))) { e.stopPropagation(); doExport(el.dataset.saveFmt, "files"); return; }
  if ((el = c("[data-fmt]"))) { if (el.getAttribute("aria-disabled") !== "true") doExport(el.dataset.fmt, "download"); return; }
  if ((el = c("[data-fmt-sel]"))) { S.fmt = el.dataset.fmtSel; renderExport(); return; }
  if ((el = c("[data-sort]"))) { S.sort = el.dataset.sort; renderOpen(); return; }
  if ((el = c("[data-tag]"))) { const i = +el.dataset.tag; step(); S.exam.tags = S.exam.tags.includes(i) ? S.exam.tags.filter((x) => x !== i) : [...S.exam.tags, i]; renderMeta(); renderHeader(); return; }
  if ((el = c("[data-pick-course]"))) { pickCourse(el.dataset.for, el.dataset.pickCourse); return; }
  if ((el = c("[data-clear-course]"))) { pickCourse(el.dataset.clearCourse, null); return; }
  if ((el = c("[data-auto-del]"))) { const q = entry(S.sel).it; step(); q.gaps[S.gapPop].auto.splice(+el.dataset.autoDel, 1); const c2 = document.querySelector(`.gap[data-gap="${S.gapPop}"]`); S.gapPop = null; openGap(c2); return; }
  if ((el = c("[data-combo]"))) { S.courseQuery = ""; openCourseMenu(el); return; }
  if ((el = c("[data-close]"))) { setDrawer(S.drawer); return; }
  if ((el = c("[data-act]"))) act(el.dataset.act, el, e);
});
function act(a, el, e) {
  const en = S.exam && entry(S.sel);
  switch (a) {
    case "open": setDrawer("open"); break;
    case "import": S.impOpen = !S.impOpen; renderEditor(); break;
    case "review": { const q = en.it; step(); q.ok = !q.ok; if (q.ok && q.keySrc === "machine") q.keySrc = "reviewed"; if (q.ok && q.kind === "unbuilt") q.kind = "fritext", q.crit = []; render(); if (q.ok) checkAllReviewed(); break; }
    case "pref": S.prefOpen = !S.prefOpen; renderEditor(); break;
    case "type": typeMenu(el, en.it); break;
    case "suggested": changeType(en.it, en.it.suggested); break;
    case "more": moreMenu(el); break;
    case "addchild": newMenu(el, true); break;
    case "retry": { const sel = el.closest(".retry").querySelector("select").value, q = en.it; el.disabled = true; el.innerHTML = `${g("loader-circle", "sm spin")}Konverterar …`;
      setTimeout(() => { q.imp.steps.push(`Konverterades igen som ${KINDS[sel]}`); if (q.kind !== sel) changeType(q, sel); else render(); S.impOpen = true; renderEditor(); }, 1200); break; }
    case "undo-ai": { const q = en.it; step(); q.key = q.kind === "flera" ? [] : null; if (q.gaps) q.gaps.forEach((x) => { x.ans = []; x.auto = []; }); q.keySrc = null; render(); toast("AI-tolkningen är ångrad. Frågan saknar facit.", { action: ["Ångra", undo, "undo-2"] }); break; }
    case "ai-one": { const q = en.it, id = S.sel; q.busy = true; renderEditor();
      setTimeout(() => { q.busy = false; step(); const aiOwns = q.key === null || q.key === q.sugg || (Array.isArray(q.key) && !q.key.length); q.sugg = q.sugg === undefined || q.sugg === null ? 0 : (q.sugg + 1) % q.opts.length; q.stale = false;
        if (aiOwns) { q.key = q.kind === "flera" ? [q.sugg] : q.sugg; q.keySrc = "machine"; q.ok = false; } if (S.sel === id) render(); else renderRows(); }, 1100); break; }
    case "add-opt": step(); en.it.opts.push(""); render(); [...document.querySelectorAll("[data-ofield]")].pop()?.focus(); break;
    case "add-gap": step(); en.it.gaps.push({ ans: [], auto: [] }); en.it.stem += ` {${en.it.gaps.length}}`; render(); break;
    case "add-rgap": step(); en.it.rgaps.push({ opts: ["", ""], key: null }); en.it.stem += ` {${en.it.rgaps.length}}`; render(); break;
    case "add-row": { const gr = en.it.grid; step(); gr.rows.push(""); gr.ticks.push(gr.cats.map(() => 0)); render(); break; }
    case "add-cat": { const gr = en.it.grid; step(); gr.cats.push(""); gr.ticks.forEach((r) => r.push(0)); render(); break; }
    case "add-crit": step(); en.it.crit.push(["", 1]); render(); [...document.querySelectorAll("[data-crit-t]")].pop()?.focus(); break;
    case "gap-close": commitGap(); closeGap(); break;
    case "gap-text": { const q = en.it, i = S.gapPop; step(); const word = q.gaps[i].ans[0];
      q.stem = q.stem.replace(`{${i + 1}}`, word); q.gaps.splice(i, 1); let k = 0; q.stem = q.stem.replace(/\{(\d+)\}/g, () => `{${++k}}`); S.gapPop = null; $("gap-pop").hidden = true; render(); break; }
    case "do-export": doExport(S.fmt, S.dest); break;
    case "more-export": closeMenus(); if (S.drawer !== "export") setDrawer("export"); break;
    case "save": closeMenus(); save(); break;
    case "saveas": openSaveAs(); break;
    case "rename": toast("Filnamnet är ändrat.", { glyph: "circle-check" }); break;
    case "addcourse": { const c = course(S.exam.course); c.mine = true; renderMeta(); toast(`${c.name} finns nu i Mina kurser.`, { glyph: "circle-check" }); break; }
    case "suggest-tags": S.tagsBusy = true; renderMeta(); setTimeout(() => { S.tagsBusy = false; renderMeta(); toast("Innehållsförslagen är uppdaterade.", { glyph: "sparkles" }); }, 1400); break;
    case "pick": startImport(); break;
    case "help": toggleHelp(); break;
    case "logout": toast("Prototypen loggar inte ut."); break;
  }
}
function startImport() {
  S.importing = { done: 0, total: 6 }; renderOpen();
  const tick = setInterval(() => {
    S.importing.done++; renderOpen();
    if (S.importing.done >= S.importing.total) {
      clearInterval(tick); S.importing = null;
      EXAMS.unshift({ id: "e9", title: "Kursprov Engelska 6", course: importCourse === "SVESVE02" ? null : importCourse, saved: `17 okt ${now()}`, t: 101, exports: {}, origin: "docx" });
      openExam("e9"); toast("Provet är inläst.", { glyph: "circle-check" });
    }
  }, 900);
}
document.addEventListener("input", (e) => {
  const t = e.target; if (!S.exam) return;
  const en = entry(S.sel);
  if (t.dataset.combo) { S.courseQuery = t.value; openCourseMenu(t); return; }
  if (t.id === "gap-in" || t.id === "sa-name") { if (t.id === "sa-name") { $("sa-err").hidden = true; t.setAttribute("aria-invalid", "false"); } return; }
  typingStep();
  const f = t.dataset.field;
  if (f === "stem") en.it.stem = readStem(t);
  else if (f === "ptext") en.it.text = t.textContent;
  else if (f === "points") { en.it.points = t.value === "" ? null : +t.value; en.it.est = false; const missing = t.value === ""; t.setAttribute("aria-invalid", String(missing)); }
  else if (f === "tick") en.it.tick = +t.value || 0;
  else if (f === "title") S.exam.title = t.value;
  else if (t.dataset.ofield !== undefined) { const q = en.it; q.opts[+t.dataset.ofield] = t.textContent; if (q.sugg !== undefined && q.sugg !== null && !q.stale) { q.stale = true; const b = document.querySelector('[data-act="ai-one"]'); if (b) { b.insertAdjacentHTML("beforeend", '<span class="badge-dot" style="top:3px;right:3px"></span>'); b.title = "Alternativen har ändrats – föreslå facit igen"; } } }
  else if (t.dataset.rofield !== undefined) { const [gi, i] = t.dataset.rofield.split(":").map(Number); en.it.rgaps[gi].opts[i] = t.textContent; }
  else if (t.dataset.cat !== undefined) en.it.grid.cats[+t.dataset.cat] = t.textContent;
  else if (t.dataset.grow !== undefined) en.it.grid.rows[+t.dataset.grow] = t.textContent;
  else if (t.dataset.critT !== undefined) en.it.crit[+t.dataset.critT][0] = t.value;
  else if (t.dataset.critP !== undefined) en.it.crit[+t.dataset.critP][1] = +t.value;
  renderHeader(); renderRows();
  if (f === "points" || f === "tick" || t.dataset.critP !== undefined) { const row = t.closest(".ptsrow"); if (f === "points" && row) { row.querySelector("#pts-msg")?.remove(); if (t.value === "") row.insertAdjacentHTML("beforeend", `<span class="errline" id="pts-msg" style="margin:0">${g("circle-alert", "sm")}Saknas</span>`); } else if (f !== "points") { const ro = document.querySelector(".ptsrow input[readonly]"); if (ro) ro.value = pts(en.it); } }
  if (S.drawer === "open") renderOpen();
});
document.addEventListener("change", (e) => { if (e.target.name === "dest") { S.dest = e.target.value; renderExport(); } });
document.addEventListener("keydown", (e) => {
  const mod = MAC ? e.metaKey : e.ctrlKey;
  if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); if (S.exam) save(); return; }
  if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (e.key === "Escape") {
    const menuOpen = ["m-export", "m-save", "m-new", "m-type", "m-more", "m-course"].some((id) => !$(id).hidden);
    if (!$("dlg-saveas").hidden) closeSaveAs(); else if (S.gapPop !== null) closeGap(); else if (menuOpen) closeMenus(); else if (S.drawer) setDrawer(S.drawer);
    return;
  }
  const openMenu = [...document.querySelectorAll(".menu")].find((m) => !m.hidden);
  if (openMenu && ["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key) && !(e.target instanceof Element && e.target.closest("input, [contenteditable]"))) {
    const items = [...openMenu.querySelectorAll('.mi:not([aria-disabled="true"]):not([disabled])')];
    if (items.length) {
      e.preventDefault();
      const i = items.indexOf(document.activeElement);
      const next = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : i < 0 ? (e.key === "ArrowDown" ? 0 : items.length - 1) : (i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items[next].focus();
    }
    return;
  }
  if (e.target.id === "gap-in" && e.key === "Enter") { commitGap(); closeGap(); return; }
  if (e.target.id === "sa-name" && e.key === "Enter") { confirmSaveAs(); return; }
  if ((e.key === "ArrowUp" || e.key === "ArrowDown") && S.exam && S.view === "workspace") {
    if (e.target instanceof Element && e.target.closest("[contenteditable], input, textarea, select, .menu, .drawer, .dialog")) return;
    e.preventDefault(); goStep(e.key === "ArrowDown" ? 1 : -1);
  }
  if ((e.key === "Enter" || e.key === " ") && e.target.matches?.("[data-tick], [data-tag], .file")) { e.preventDefault(); e.target.click(); }
});
document.addEventListener("focusout", (e) => { if (e.target.id === "gap-in") setTimeout(() => { if (S.gapPop !== null && !$("gap-pop").contains(document.activeElement)) { commitGap(); closeGap(); } }, 120); });
// Drag-over feedback for the intake zone.
document.addEventListener("dragover", (e) => { const d = e.target.closest?.("#drop"); if (d && !d.classList.contains("off")) { e.preventDefault(); d.classList.add("over"); } });
document.addEventListener("dragleave", (e) => e.target.closest?.("#drop")?.classList.remove("over"));
document.addEventListener("drop", (e) => { const d = e.target.closest?.("#drop"); if (d) { e.preventDefault(); d.classList.remove("over"); startImport(); } });

$("b-open").onclick = () => setDrawer("open");
$("b-title").onclick = () => setDrawer("meta");
$("b-save").onclick = save;
$("b-save-menu").onclick = (e) => { e.stopPropagation(); $("m-save").hidden ? place($("m-save"), $("b-save-menu"), phoneMq.matches ? "right" : "right") : closeMenus(); renderHeader(); };
$("b-export").onclick = (e) => { e.stopPropagation(); $("m-export").hidden ? openExportMenu() : closeMenus(); };
$("b-new").onclick = (e) => { e.stopPropagation(); $("m-new").hidden ? newMenu($("b-new"), false) : closeMenus(); };
$("b-ai-all").onclick = () => suggestAll();
$("b-undo").onclick = undo; $("b-redo").onclick = redo;
$("b-rail").onclick = () => { const on = !document.body.classList.contains("rail"); document.body.classList.toggle("rail", on);
  $("b-rail").setAttribute("aria-pressed", String(on)); const t = on ? "Fäll ut menyn" : "Fäll ihop menyn"; $("b-rail").title = t; $("b-rail").setAttribute("aria-label", t); };
$("b-nav").onclick = () => { const on = !document.body.classList.contains("nav-open"); document.body.classList.toggle("nav-open", on); $("b-nav").setAttribute("aria-expanded", String(on)); };
$("b-nav-close").onclick = $("nav-backdrop").onclick = () => { document.body.classList.remove("nav-open"); $("b-nav").setAttribute("aria-expanded", "false"); };
$("brand").onclick = (e) => { e.preventDefault(); setView("home"); };
function toggleHelp(force) { const on = force ?? $("helppanel").hidden; $("helppanel").hidden = !on; $("b-help").setAttribute("aria-expanded", String(on)); document.body.classList.remove("nav-open"); }
$("b-help").onclick = () => toggleHelp(); $("help-close").onclick = () => toggleHelp(false);
$("b-logout").onclick = () => toast("Prototypen loggar inte ut.");
$("p-prev").onclick = () => goStep(-1); $("p-next").onclick = () => goStep(1);
$("p-pick").onclick = () => document.body.classList.add("show-list");
$("list-back").onclick = () => document.body.classList.remove("show-list");
$("toast-close").onclick = hideToast;
$("sa-cancel").onclick = closeSaveAs; $("sa-ok").onclick = confirmSaveAs; $("scrim").onclick = closeSaveAs;
$("keys").innerHTML = [[kbd("S"), "Spara"], [kbd("Z"), "Ångra"], [kbd("Z", true), "Gör om"], ["↑ ↓", "Föregående och nästa fråga i listan"]].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
phoneMq.addEventListener("change", placeForWidth);

// ───────── Start, and the URL hash that opens a reviewed state ─────────
// Keys: view=home|vault|<nav id>; empty; importing; q=<label>; imp; pref; drawer=open|export|meta;
// menu=export|save|new|type|more|child|course; dlg=saveas[&err]; pop=gap; toast=reviewed|resume|qti;
// dirty; change=<kind>; ready; othercourse; nocourse; tagsbusy; list; nav; rail; help; checklist; sort=senaste; fmt; dest=files
const H = Object.fromEntries(location.hash.slice(1).split("&").filter(Boolean).map((p) => { const [k, v = "1"] = p.split("="); return [k, decodeURIComponent(v)]; }));
renderNav();
if (H.empty || H.importing) { S.exam = null; } else { S.exam = makeExam(); S.saved = snap(); S.sel = "q3"; }
if (S.exam && H.ready) { for (const { it } of qs()) { it.ok = true; it.converting = false; if (it.points === null) it.points = 1; if (it.kind === "unbuilt") { it.kind = "fritext"; it.crit = []; } if (it.keySrc === "machine") it.keySrc = "reviewed"; } S.saved = snap(); }
if (S.exam && H.othercourse) { S.exam.course = "SVESVE03"; S.exam.tags = []; S.saved = snap(); }
if (S.exam && H.nocourse) { S.exam.course = null; S.exam.tags = []; S.saved = snap(); }
if (S.exam && H.q) { const e = entries().find((x) => x.lab === H.q); if (e) S.sel = e.it.id; }
if (H.imp) S.impOpen = true;
if (H.pref) S.prefOpen = true;
if (H.sort) S.sort = H.sort;
if (H.fmt) S.fmt = H.fmt;
if (H.dest) S.dest = H.dest;
if (H.checklist) S.checklist = true;
if (S.exam && H.dirty) { step(); entry(S.sel).it.stem += " Motivera kort."; S.typing = null; }
if (H.rail) { document.body.classList.add("rail"); $("b-rail").setAttribute("aria-pressed", "true"); }
setView(H.view || "workspace");
placeForWidth();
render();
if (H.empty) setDrawer("open");
if (H.importing) { setDrawer("open"); S.importing = { done: 4, total: 12 }; renderOpen(); }
if (H.drawer) setDrawer(H.drawer);
if (S.exam && H.change) changeType(entry(S.sel).it, H.change);
if (H.list) document.body.classList.add("show-list");
if (H.nav) { document.body.classList.add("nav-open"); $("b-nav").setAttribute("aria-expanded", "true"); }
if (H.help) toggleHelp(true);
if (H.tagsbusy) { S.tagsBusy = true; renderMeta(); }
if (H.dlg === "saveas") openSaveAs(!!H.err);
if (H.toast === "reviewed") toast("Alla frågor är granskade", { glyph: "circle-check", action: ["Exportera", openExportMenu, "download"], sticky: true });
if (H.toast === "resume" || H.resume) suggestAll(true);
if (H.toast === "qti") toast("QTI sparad i Mina filer. Exam.net tappar en del vid import.", { glyph: "list-checks", action: ["Visa listan", () => setDrawer("export")], sticky: true });
requestAnimationFrame(() => {
  const m = H.menu;
  if (m === "export") openExportMenu();
  if (m === "save") place($("m-save"), $("b-save-menu"), "right");
  if (m === "new") newMenu($("b-new"), false);
  if (m === "type") typeMenu(document.querySelector('[data-act="type"]'), entry(S.sel).it);
  if (m === "more") moreMenu(document.querySelector('[data-act="more"]'));
  if (m === "child") newMenu(document.querySelector('[data-act="addchild"]'), true);
  if (m === "course") { const i = document.querySelector("#meta-course, #imp-course"); S.courseQuery = ""; openCourseMenu(i); }
  if (H.pop === "gap") { const c2 = document.querySelector(".gap"); if (c2) openGap(c2); }
  if (H.rgap) { S.curGap = +H.rgap; renderEditor(); }
});
// The converting question finishes on its own, as a running import would.
if (S.exam && !H.keepconverting) setTimeout(() => { const q = S.exam?.items.find((x) => x.id === "q12"); if (q?.converting) { const clean = S.saved === snap(); q.converting = false; q.imp.steps = ["Typ: Fritext"]; if (clean) S.saved = snap(); render(); } }, 9000);
})();
