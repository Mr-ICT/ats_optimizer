/* ─── ATS Optimizer Frontend ──────────────────────────────────────────────
   Handles:
   - Drag & drop / file picker
   - Form validation
   - Fetch API to /analyze
   - Animated results rendering
   ─────────────────────────────────────────────────────────────────────── */

"use strict";

// ── DOM refs ────────────────────────────────────────────────────────────────
const dropZone      = document.getElementById("drop-zone");
const resumeInput   = document.getElementById("resume-input");
const fileLabel     = document.getElementById("file-label");
const jdInput       = document.getElementById("jd-input");
const charCount     = document.getElementById("char-count");
const analyzeBtn    = document.getElementById("analyze-btn");

const uploadSection = document.getElementById("upload-section");
const loadingScreen = document.getElementById("loading-screen");
const resultsSection = document.getElementById("results-section");
const errorScreen   = document.getElementById("error-screen");
const errorMessage  = document.getElementById("error-message");

const reanalyzeBtn  = document.getElementById("reanalyze-btn");
const errorRetryBtn = document.getElementById("error-retry-btn");

let selectedFile = null;

// ── File Selection ────────────────────────────────────────────────────────
dropZone.addEventListener("click", () => resumeInput.click());
dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});
resumeInput.addEventListener("change", () => {
  if (resumeInput.files[0]) setFile(resumeInput.files[0]);
});

function setFile(file) {
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["pdf", "docx"].includes(ext)) {
    alert("Only PDF and DOCX files are supported.");
    return;
  }
  selectedFile = file;
  fileLabel.textContent = `✓ ${file.name} (${formatBytes(file.size)})`;
  checkReady();
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// ── JD Character Count ────────────────────────────────────────────────────
jdInput.addEventListener("input", () => {
  charCount.textContent = `${jdInput.value.length} chars`;
  checkReady();
});

function checkReady() {
  const ready = selectedFile && jdInput.value.trim().length >= 50;
  analyzeBtn.disabled = !ready;
}

// ── Analyze ───────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", runAnalysis);

async function runAnalysis() {
  if (!selectedFile || jdInput.value.trim().length < 50) return;

  showScreen("loading");
  animateLoadingSteps();

  const formData = new FormData();
  formData.append("resume", selectedFile);
  formData.append("job_description", jdInput.value.trim());

  try {
    const res = await fetch("/analyze", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      throw new Error(data.error || "Analysis failed");
    }

    renderResults(data);
    showScreen("results");
  } catch (err) {
    errorMessage.textContent = err.message || "Unknown error occurred.";
    showScreen("error");
  }
}

// ── Loading Step Animation ────────────────────────────────────────────────
function animateLoadingSteps() {
  const steps = document.querySelectorAll(".step");
  steps.forEach(s => s.classList.remove("active", "done"));
  steps[0].classList.add("active");

  const delays = [0, 800, 2000, 3200, 4500];
  steps.forEach((step, i) => {
    if (i === 0) return;
    setTimeout(() => {
      steps[i - 1].classList.remove("active");
      steps[i - 1].classList.add("done");
      step.classList.add("active");
    }, delays[i]);
  });
}

// ── Screen Management ─────────────────────────────────────────────────────
function showScreen(name) {
  uploadSection.hidden = name !== "upload";
  loadingScreen.hidden = name !== "loading";
  resultsSection.hidden = name !== "results";
  errorScreen.hidden = name !== "error";
}

reanalyzeBtn.addEventListener("click", () => showScreen("upload"));
errorRetryBtn.addEventListener("click", () => showScreen("upload"));

// ── Render Results ────────────────────────────────────────────────────────
function renderResults(data) {
  renderScoreHero(data);
  renderKeywords(data.keyword_analysis);
  renderIssues(data.all_issues || []);
  renderSections(data.sections_detected || {}, data.parse_info || {});
  renderSemantic(data.semantic_similarity);
  renderAIFeedback(data.ai_feedback || {});
}

// Score gauge + breakdown bars
function renderScoreHero(data) {
  const score = data.ats_score || 0;
  const grade = data.grade || "—";
  const color = { Excellent: "#22c55e", Good: "#4f8ef7", Fair: "#f97316", Poor: "#ef4444" }[grade] || "#fff";

  // Animate number
  animateNumber(document.getElementById("score-number"), 0, score, 1200);

  const gradeEl = document.getElementById("score-grade");
  gradeEl.textContent = grade;
  gradeEl.style.color = color;

  // Gauge fill: path length ~251 units for semicircle
  const gaugeFill = document.getElementById("gauge-fill");
  const offset = 251 - (score / 100) * 251;
  setTimeout(() => {
    gaugeFill.style.transition = "stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)";
    gaugeFill.style.strokeDashoffset = offset;
  }, 100);

  // Breakdown bars
  const bd = data.scoring_breakdown || {};
  const barsEl = document.getElementById("breakdown-bars");
  barsEl.innerHTML = "";

  const barDefs = [
    { key: "semantic_similarity", label: "Semantic Similarity (40%)" },
    { key: "keyword_match",       label: "Keyword Match (30%)" },
    { key: "formatting",          label: "Formatting (15%)" },
    { key: "content_quality",     label: "Content Quality (15%)" },
  ];

  barDefs.forEach(({ key, label }) => {
    const sub = bd[key] || {};
    const s = sub.score || 0;
    const barColor = s >= 70 ? "#22c55e" : s >= 50 ? "#4f8ef7" : s >= 35 ? "#f97316" : "#ef4444";
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <span class="bar-label">${label}</span>
      <div class="bar-track">
        <div class="bar-fill" style="width:0%;background:${barColor}" data-target="${s}"></div>
      </div>
      <span class="bar-value">${s}</span>
    `;
    barsEl.appendChild(row);
  });

  // Animate bars after a tick
  setTimeout(() => {
    document.querySelectorAll(".bar-fill[data-target]").forEach(el => {
      el.style.width = el.dataset.target + "%";
    });
  }, 150);
}

// Keywords
function renderKeywords(kw) {
  if (!kw) return;
  const badge = document.getElementById("kw-badge");
  badge.textContent = `${kw.match_percentage}% match`;

  const statsEl = document.getElementById("keyword-stats");
  statsEl.innerHTML = `
    <div class="kw-stat found">
      <span class="kw-stat-num">${kw.matched_count}</span>
      <span class="kw-stat-label">Found</span>
    </div>
    <div class="kw-stat missing">
      <span class="kw-stat-num">${(kw.missing_keywords || []).length}</span>
      <span class="kw-stat-label">Missing</span>
    </div>
    <div class="kw-stat">
      <span class="kw-stat-num">${kw.total_jd_keywords}</span>
      <span class="kw-stat-label">Total JD</span>
    </div>
  `;

  const listsEl = document.getElementById("keyword-lists");
  listsEl.innerHTML = "";

  const maxShow = 12;

  if ((kw.found_keywords || []).length > 0) {
    const sec = document.createElement("div");
    sec.className = "keyword-section";
    sec.innerHTML = `<div class="keyword-section-title">✓ Found in Resume</div>
      <div class="keyword-tags">${kw.found_keywords.slice(0, maxShow).map(k =>
        `<span class="kw-tag found-tag">${escHtml(k)}</span>`
      ).join("")}</div>`;
    listsEl.appendChild(sec);
  }

  if ((kw.missing_keywords || []).length > 0) {
    const sec = document.createElement("div");
    sec.className = "keyword-section";
    sec.innerHTML = `<div class="keyword-section-title">✗ Missing from Resume</div>
      <div class="keyword-tags">${kw.missing_keywords.slice(0, maxShow).map(k =>
        `<span class="kw-tag missing-tag">${escHtml(k)}</span>`
      ).join("")}</div>`;
    listsEl.appendChild(sec);
  }
}

// Issues
function renderIssues(issues) {
  const badge = document.getElementById("issues-badge");
  const list = document.getElementById("issues-list");

  badge.textContent = `${issues.length} issue${issues.length !== 1 ? "s" : ""}`;

  if (issues.length === 0) {
    list.innerHTML = `<p class="no-issues">✓ No major formatting issues detected</p>`;
    return;
  }

  list.innerHTML = issues.map(issue => `
    <div class="issue-item">
      <span class="issue-icon">⚠</span>
      <span>${escHtml(issue)}</span>
    </div>
  `).join("");
}

// Sections & parse info
function renderSections(sections, parseInfo) {
  const el = document.getElementById("sections-content");
  const allSections = ["experience", "education", "skills", "summary", "projects", "certifications"];
  const chips = allSections.map(s =>
    `<span class="section-chip ${sections[s] ? "present" : "absent"}">
      ${sections[s] ? "✓" : "✗"} ${capitalize(s)}
    </span>`
  ).join("");

  const confPct = ((parseInfo.confidence || 0) * 100).toFixed(0);
  const confColor = confPct >= 80 ? "#22c55e" : confPct >= 50 ? "#f97316" : "#ef4444";

  el.innerHTML = `
    <div class="section-chips">${chips}</div>
    <div class="parse-info">
      <div class="parse-label">Parsing Confidence</div>
      <div class="parse-badge">${confPct}% · ${parseInfo.word_count || 0} words · ${parseInfo.pages || 0} page(s)</div>
      <div class="confidence-bar">
        <div class="confidence-fill" style="width:${confPct}%;background:${confColor}"></div>
      </div>
      ${(parseInfo.warnings || []).slice(0, 3).map(w =>
        `<div class="issue-item"><span class="issue-icon">ℹ</span><span>${escHtml(w)}</span></div>`
      ).join("")}
    </div>
  `;
}

// Semantic
function renderSemantic(sim) {
  const el = document.getElementById("semantic-content");
  const pct = sim || 0;
  const desc = pct >= 75 ? "Strong alignment with job requirements" :
               pct >= 55 ? "Moderate alignment — tailor more to JD language" :
               "Low alignment — significantly rephrase to match JD vocabulary";

  el.innerHTML = `
    <div class="semantic-score-display">${pct}%</div>
    <p class="semantic-desc">${desc}</p>
    <p class="semantic-desc" style="margin-top:.5rem;font-size:.78rem;color:var(--text3)">
      Computed via Sentence-Transformers cosine similarity (all-MiniLM-L6-v2)
    </p>
  `;
}

// AI Feedback
function renderAIFeedback(fb) {
  const grid = document.getElementById("ai-grid");
  grid.innerHTML = "";

  // Top Priority
  if (fb.top_priority) {
    const card = aiCard("🎯 Top Priority", `<div class="priority-box">${escHtml(fb.top_priority)}</div>`);
    grid.appendChild(card);
  }

  // Improvements
  if ((fb.improvements || []).length > 0) {
    const items = fb.improvements.slice(0, 5).map(imp =>
      `<li><strong>${escHtml(imp.section || "")}:</strong> ${escHtml(imp.suggestion || imp.issue || "")}</li>`
    ).join("");
    const card = aiCard("📝 Improvements", `<ul>${items}</ul>`);
    grid.appendChild(card);
  }

  // Missing Skills
  if ((fb.missing_skills || []).length > 0) {
    const tags = fb.missing_skills.slice(0, 15).map(s =>
      `<span class="ai-tag">${escHtml(s)}</span>`
    ).join("");
    const card = aiCard("🔧 Missing Skills", `<div>${tags}</div>`);
    grid.appendChild(card);
  }

  // Bullet Rewrites
  if ((fb.bullet_rewrites || []).length > 0) {
    const rewrites = fb.bullet_rewrites.slice(0, 2).map(r => `
      <div class="rewrite-block">
        <div class="rewrite-label">Original</div>
        <div>${escHtml(r.original || "")}</div>
      </div>
      <div class="rewrite-block new-version">
        <div class="rewrite-label">Improved</div>
        <div>${escHtml(r.rewritten || "")}</div>
      </div>
    `).join("");
    const card = aiCard("✍️ Bullet Rewrites", rewrites);
    grid.appendChild(card);
  }

  // Summary suggestion
  if (fb.summary_suggestion) {
    const card = aiCard("📌 Summary Suggestion", `<p>${escHtml(fb.summary_suggestion)}</p>`);
    grid.appendChild(card);
  }

  // Source badge
  if (fb.source) {
    const src = fb.source === "groq_llm" ? "Powered by Groq LLM" : "Rule-based fallback (add GROQ_API_KEY for LLM suggestions)";
    const note = document.createElement("div");
    note.style.cssText = "grid-column:1/-1;font-family:var(--font-mono);font-size:.7rem;color:var(--text3);text-align:center;padding:.5rem";
    note.textContent = src;
    grid.appendChild(note);
  }
}

function aiCard(title, bodyHtml) {
  const div = document.createElement("div");
  div.className = "ai-card";
  div.innerHTML = `
    <div class="ai-card-title">${title}</div>
    <div class="ai-card-body">${bodyHtml}</div>
  `;
  return div;
}

// ── Utilities ─────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function animateNumber(el, from, to, duration) {
  const start = performance.now();
  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    el.textContent = Math.round(from + (to - from) * easeOut(progress));
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
// ── Splash Loader ─────────────────────────────────────────────────────────
(function() {
  const splash    = document.getElementById("splash-loader");
  const bar       = document.getElementById("splash-bar");
  const pct       = document.getElementById("splash-percent");
  const duration  = 4000; // 4 seconds
  const interval  = 40;   // update every 40ms
  const steps     = duration / interval;
  let   current   = 0;

  const timer = setInterval(() => {
    current++;
    // Ease-out so it slows near 100%
    const progress = Math.round((1 - Math.pow(1 - current / steps, 2)) * 100);
    bar.style.width = progress + "%";
    pct.textContent = progress + "%";

    if (current >= steps) {
      clearInterval(timer);
      bar.style.width = "100%";
      pct.textContent = "100%";
      setTimeout(() => splash.classList.add("hidden"), 300);
    }
  }, interval);
})();
showScreen("upload");