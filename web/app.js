// RedactAgent review UI - vanilla JS, no build step, works offline.
const $ = (s) => document.querySelector(s);
const state = { info: null, job: null, page: 0, findings: [], file: null, hl: null };
const ACTION_TEXT = { redact: "redact", pseudonymize: "pseudonymise", generalize_year: "year only", keep: "keep" };

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
}

async function init() {
  state.info = await api("/api/info");
  const i = state.info;
  $("#models").innerHTML = [
    `<span class="chip"><span class="dot ${i.text_model_online ? "on" : ""}"></span>LLM ${i.text_model}</span>`,
    `<span class="chip"><span class="dot ${i.vision_model_online ? "on" : ""}"></span>VLM ${i.vision_model}</span>`,
    `<span class="chip">backend: ${i.backend}</span>`,
    `<span class="chip">&#128274; offline</span>`,
  ].join("");
  $("#llmName").textContent = i.text_model;
  $("#vlmName").textContent = i.vision_model;
  $("#policy").innerHTML = i.policies.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
  $("#policy").onchange = onPolicy;
  onPolicy(true);
  $("#legend").innerHTML = Object.entries(i.categories)
    .map(([k, v]) => `<span style="background:${v.color}">${v.name}</span>`).join("");
  const s = await api("/api/samples");
  $("#sample").innerHTML = s.samples.map((n) => `<option>${n}</option>`).join("");
  $("#sample").onchange = () => { state.file = null; $("#dropText").textContent = "or drop a PDF / scan here"; previewSample(); };
  previewSample();
  setupDrop();
  $("#run").onclick = run;
  $("#export").onclick = exportJob;
  refreshAudit();
}

function previewSample() {
  const n = $("#sample").value;
  if (!n || n.endsWith(".pdf")) return;
  $("#orig").src = `/api/samples/${encodeURIComponent(n)}`;
  $("#emptyOrig").classList.add("hidden");
  $("#overlay").innerHTML = "";
  $("#red").removeAttribute("src");
  $("#emptyRed").classList.remove("hidden");
}

function setupDrop() {
  const d = $("#drop");
  d.onclick = () => $("#file").click();
  $("#file").onchange = (e) => pick(e.target.files[0]);
  d.ondragover = (e) => { e.preventDefault(); d.classList.add("over"); };
  d.ondragleave = () => d.classList.remove("over");
  d.ondrop = (e) => { e.preventDefault(); d.classList.remove("over"); pick(e.dataTransfer.files[0]); };
}
function pick(f) {
  if (!f) return;
  state.file = f;
  $("#dropText").textContent = "✓ " + f.name;
  if (f.type.startsWith("image/")) { $("#orig").src = URL.createObjectURL(f); $("#emptyOrig").classList.add("hidden"); }
}

async function onPolicy(initial) {
  const p = state.info.policies.find((x) => x.id === $("#policy").value);
  $("#policyDesc").textContent = p.description;
  $("#policyLegal").textContent = "Legal basis: " + p.legal_basis;
  if (initial === true || !state.job || state.job.status !== "done") return;
  const r = await api(`/api/jobs/${state.job.id}/review`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ policy: p.id }),
  });
  state.findings = r.findings;
  renderAll();
  refreshAudit();
}

async function run() {
  const fd = new FormData();
  if (state.file) fd.append("file", state.file); else fd.append("sample", $("#sample").value);
  fd.append("policy", $("#policy").value);
  const layers = [...document.querySelectorAll(".toggle input:checked")].map((x) => x.value);
  fd.append("layers", layers.join(","));
  $("#run").disabled = true;
  $("#progress").classList.remove("hidden");
  $("#stats").classList.add("hidden");
  $("#downloads").classList.add("hidden");
  $("#list").innerHTML = "";
  $("#overlay").innerHTML = "";
  $("#red").removeAttribute("src");
  try {
    const job = await api("/api/jobs", { method: "POST", body: fd });
    poll(job.id);
  } catch (e) { alert(e.message); $("#run").disabled = false; }
}

async function poll(id) {
  const j = await api(`/api/jobs/${id}`);
  $("#bar").style.width = Math.round(j.progress * 100) + "%";
  $("#stage").textContent = j.stage || j.status;
  if (j.status === "done") { state.job = j; state.findings = j.findings; state.page = 0; done(); return; }
  if (j.status === "error") { $("#stage").textContent = "Error: " + j.error; $("#run").disabled = false; return; }
  setTimeout(() => poll(id), 400);
}

function done() {
  $("#run").disabled = false;
  $("#progress").classList.add("hidden");
  $("#stats").classList.remove("hidden");
  $("#emptyOrig").classList.add("hidden");
  $("#emptyRed").classList.add("hidden");
  const j = state.job;
  $("#docType").textContent = j.doc_type || "";
  const t = j.timings;
  $("#kTime").textContent = (t.total || 0).toFixed(1) + "s";
  const fmt = (k, label) => (t[k] !== undefined ? `${label} ${t[k].toFixed(2)}s` : null);
  $("#timing").innerHTML = [fmt("ocr", "OCR"), fmt("rules", "rules"), fmt("llm", "LLM"), fmt("vlm", "VLM")]
    .filter(Boolean).join(" &middot; ") + (j.tokens.llm_completion ? `<br>${j.tokens.llm_prompt}+${j.tokens.llm_completion} LLM tokens` : "");
  const pager = $("#pager");
  if (j.pages > 1) {
    pager.classList.remove("hidden");
    pager.innerHTML = Array.from({ length: j.pages }, (_, i) => `<button data-p="${i}">Page ${i + 1}</button>`).join("");
    pager.querySelectorAll("button").forEach((b) => (b.onclick = () => { state.page = +b.dataset.p; renderAll(); }));
  } else pager.classList.add("hidden");
  renderAll();
  refreshAudit();
}

function renderAll() {
  const j = state.job;
  $("#pager").querySelectorAll("button").forEach((b) => b.classList.toggle("on", +b.dataset.p === state.page));
  $("#orig").src = `/api/jobs/${j.id}/page/${state.page}.png?view=original`;
  refreshRedacted();
  renderOverlay();
  renderList();
  const fs = state.findings;
  $("#kFind").textContent = fs.length;
  $("#kRed").textContent = fs.filter((f) => f.accepted && f.action !== "keep").length;
  const src = { rule: 0, llm: 0, vlm: 0, cv: 0 };
  fs.forEach((f) => f.sources.forEach((s) => (src[s] = (src[s] || 0) + 1)));
  $("#srcs").innerHTML = Object.entries(src).filter(([, n]) => n)
    .map(([s, n]) => `<span class="badge ${s}">${s.toUpperCase()} ${n}</span>`).join("")
    + ((j.warnings || []).length ? `<div class="warnbox">&#9888; ${j.warnings.length} region(s) with ink the OCR could not read &mdash; check the dashed boxes</div>`
      : `<div class="okbox">&#10003; every ink region on the page was read</div>`);
}

function refreshRedacted() {
  $("#red").src = `/api/jobs/${state.job.id}/page/${state.page}.png?view=redacted&t=${Date.now()}`;
}

function color(cat) { return (state.info.categories[cat] || { color: "#f00" }).color; }

function renderOverlay() {
  const [w, h] = state.job.page_sizes[state.page];
  const svg = $("#overlay");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("preserveAspectRatio", "none");
  const warn = (state.job.warnings || []).filter((x) => x.page === state.page).map((x) => {
    const [x0, y0, x1, y1] = x.bbox;
    return `<rect x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}" fill="#f59e0b" fill-opacity=".15"
      stroke="#f59e0b" stroke-width="4" stroke-dasharray="10 6" style="pointer-events:none"></rect>`;
  }).join("");
  svg.innerHTML = warn + state.findings.filter((f) => f.page === state.page).map((f) => {
    const [x0, y0, x1, y1] = f.bbox;
    const c = color(f.category);
    return `<rect data-id="${f.id}" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}" rx="3"
      fill="${c}" fill-opacity="${f.action === "keep" ? 0.08 : 0.25}" stroke="${c}" stroke-width="3"
      class="${f.accepted ? "" : "rej"} ${state.hl === f.id ? "hl" : ""}"></rect>`;
  }).join("");
  svg.querySelectorAll("rect").forEach((r) => {
    r.onclick = () => toggle(r.dataset.id);
    r.onmousemove = (e) => showTip(e, r.dataset.id);
    r.onmouseleave = hideTip;
  });
}

function renderList() {
  const groups = {};
  state.findings.filter((f) => f.page === state.page).forEach((f) => (groups[f.category] = groups[f.category] || []).push(f));
  const order = Object.keys(state.info.categories);
  $("#list").innerHTML = order.filter((c) => groups[c]).map((c) => `
    <div class="group"><h4><i style="background:${color(c)}"></i>${state.info.categories[c].name} <span class="muted">(${groups[c].length})</span></h4>
    ${groups[c].map((f) => `
      <div class="item ${f.accepted ? "" : "rej"} ${state.hl === f.id ? "hl" : ""}" data-id="${f.id}">
        <input type="checkbox" ${f.accepted ? "checked" : ""}>
        <div><div class="txt">${esc(f.text)}</div>
          <div class="meta">${f.sources.map((s) => `<span class="badge ${s}">${s.toUpperCase()}</span>`).join("")}
            <span class="act ${f.action}">${ACTION_TEXT[f.action] || f.action}${f.label ? " → " + esc(f.label) : ""}</span>
            ${f.role ? `<span class="role">${f.role}</span>` : ""}</div>
        </div>
      </div>`).join("")}</div>`).join("") || `<p class="muted">No findings.</p>`;
  $("#list").querySelectorAll(".item").forEach((el) => {
    el.querySelector("input").onclick = (e) => { e.stopPropagation(); toggle(el.dataset.id); };
    el.onmouseenter = () => { state.hl = el.dataset.id; renderOverlay(); };
    el.onmouseleave = () => { state.hl = null; renderOverlay(); };
  });
}

async function toggle(id) {
  const f = state.findings.find((x) => x.id === id);
  const r = await api(`/api/jobs/${state.job.id}/review`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decisions: { [id]: !f.accepted } }),
  });
  state.findings = r.findings;
  renderAll();
  refreshAudit();
}

function showTip(e, id) {
  const f = state.findings.find((x) => x.id === id);
  const t = $("#tip");
  t.innerHTML = `<b>${state.info.categories[f.category].name}</b> &middot; ${(f.confidence * 100).toFixed(0)}%<br>${esc(f.text)}<br>
    <span style="opacity:.75">${esc(f.reason || "")}</span><br>sources: ${f.sources.join(", ")}${f.role ? " &middot; role: " + f.role : ""}`;
  t.style.left = e.clientX + 14 + "px";
  t.style.top = e.clientY + 14 + "px";
  t.classList.remove("hidden");
}
function hideTip() { $("#tip").classList.add("hidden"); }

async function exportJob() {
  $("#export").disabled = true;
  try {
    const r = await api(`/api/jobs/${state.job.id}/export`, { method: "POST" });
    const base = `/api/jobs/${state.job.id}/download`;
    $("#downloads").innerHTML = `
      <a href="${base}/redacted.pdf" target="_blank">&#11015; redacted.pdf</a>
      <a href="${base}/deidentified.txt" target="_blank">&#11015; de-identified text</a>
      <a href="${base}/report.json" target="_blank">&#11015; redaction report (JSON)</a>
      <div class="hash">PDF sha256 ${r.pdf_sha256.slice(0, 32)}&hellip;<br>audit entry ${r.audit_hash.slice(0, 32)}&hellip;</div>`;
    $("#downloads").classList.remove("hidden");
    refreshAudit();
  } finally { $("#export").disabled = false; }
}

async function refreshAudit() {
  const a = await api("/api/audit" + (state.job ? `?job=${state.job.id}` : ""));
  const v = a.verify;
  $("#audit").innerHTML = (v.ok ? `<span class="audit-ok">&#10003; hash chain intact</span>` : `<span class="audit-bad">&#10007; chain broken at #${v.broken_at}</span>`)
    + ` &middot; ${v.entries} entries` +
    (a.entries.length ? `<div class="audit-list">${a.entries.slice(-8).reverse().map((e) =>
      `<div>${e.ts.slice(11, 19)} ${e.event} &middot; ${e.actor} &middot; ${e.hash.slice(0, 10)}</div>`).join("")}</div>` : "");
}

function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]); }
init();
