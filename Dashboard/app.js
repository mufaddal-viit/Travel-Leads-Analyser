// ── Config guard ──────────────────────────────────────────────────────────────
// Fail fast if config.js hasn't been filled in yet.
if (!CONFIG?.SPREADSHEET_ID || CONFIG.SPREADSHEET_ID.includes("YOUR_")) {
  document.getElementById("loading-overlay").classList.add("visible");
  document.querySelector(".spinner").style.display = "none";
  document.querySelector(".loading-overlay p").style.display = "none";
  document.getElementById("loading-overlay").innerHTML = `
    <div class="config-error">
      <h3>Configuration Required</h3>
      <p>
        Open <code>config.js</code> and set your<br/>
        <code>SPREADSHEET_ID</code> and <code>API_KEY</code>.
      </p>
    </div>`;
  throw new Error("CONFIG values not set in config.js");
}

// ── Constants ─────────────────────────────────────────────────────────────────
const PAGE_SIZE = 50;
const TODAY     = new Date().toISOString().slice(0, 10); // "YYYY-MM-DD"

// Column indices in the Google Sheet (0-based, matching SHEET_HEADERS order)
const COL = {
  NAME: 0, EMAIL: 1, COMPANY: 2, JOB_TITLE: 3, MESSAGE: 4,
  SCORE: 5, INDUSTRY: 6, NEED: 7, ACTION: 8, DATE: 9,
};

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  page:        1,
  totalRows:   0,
  leads:       [],   // raw leads fetched for the current page
  loading:     false,
  filter:      "all",
  search:      "",
  dateFrom:    TODAY,  // default to today
  dateTo:      TODAY,  // default to today
  fetchStatus: "idle", // "idle" | "loading" | "ok" | "error"
  fetchError:  "",
  lastFetched: null,   // Date object, set after each successful fetch
};

// ── Google Sheets API helpers ─────────────────────────────────────────────────

/** Build a Sheets API v4 URL for a given A1 range. */
function sheetsUrl(range) {
  const base = "https://sheets.googleapis.com/v4/spreadsheets";
  return `${base}/${CONFIG.SPREADSHEET_ID}/values/${encodeURIComponent(range)}?key=${CONFIG.API_KEY}`;
}

/**
 * Fetch the total number of data rows (excluding the header).
 * Only reads column A to minimise data transfer.
 */
async function fetchRowCount() {
  const res  = await fetch(sheetsUrl(`${CONFIG.SHEET_NAME}!A2:A`));
  const json = await res.json();
  if (json.error) throw new Error(json.error.message);
  return json.values ? json.values.length : 0;
}

/**
 * Fetch exactly PAGE_SIZE rows for the given page number.
 * Row 1 is the header, so data starts at row 2.
 *   Page 1 → rows  2 – 51
 *   Page 2 → rows 52 – 101  …etc.
 */
async function fetchPageData(page) {
  const startRow = (page - 1) * PAGE_SIZE + 2;
  const endRow   = startRow + PAGE_SIZE - 1;
  const range    = `${CONFIG.SHEET_NAME}!A${startRow}:J${endRow}`;
  const res      = await fetch(sheetsUrl(range));
  const json     = await res.json();
  if (json.error) throw new Error(json.error.message);
  return (json.values || []).map(rowToLead);
}

/** Map a raw Sheets row array to a typed lead object. */
function rowToLead(row) {
  return {
    name:               (row[COL.NAME]     || "").trim(),
    email:              (row[COL.EMAIL]    || "").trim(),
    company_name:       (row[COL.COMPANY]  || "").trim(),
    job_title:          (row[COL.JOB_TITLE]|| "").trim(),
    message:            (row[COL.MESSAGE]  || "").trim(),
    lead_score:         parseInt(row[COL.SCORE], 10) || 0,
    industry:           (row[COL.INDUSTRY] || "").trim(),
    business_need:      (row[COL.NEED]     || "").trim(),
    recommended_action: (row[COL.ACTION]   || "").trim(),
    processed_at:       (row[COL.DATE]     || "").trim(),
  };
}

// ── Load pipeline ─────────────────────────────────────────────────────────────

/**
 * Main entry point for fetching and rendering a page.
 * Fetches the row count once (caches in state.totalRows), then fetches
 * exactly PAGE_SIZE rows from Google Sheets for the requested page.
 */
async function loadPage(page) {
  if (state.loading) return;
  state.loading     = true;
  state.fetchStatus = "loading";
  setLoading(true);

  try {
    // Fetch total count only on the first load
    if (state.totalRows === 0) {
      state.totalRows = await fetchRowCount();
    }

    state.leads       = await fetchPageData(page);
    state.page        = page;
    state.fetchStatus = "ok";
    state.fetchError  = "";
    state.lastFetched = new Date();

    renderAll();
  } catch (err) {
    state.fetchStatus = "error";
    state.fetchError  = err.message;
    showError(err.message);
  } finally {
    state.loading = false;
    setLoading(false);
  }
}

// ── Filtering ─────────────────────────────────────────────────────────────────

function tier(score) {
  return score >= 70 ? "high" : score >= 40 ? "mid" : "low";
}

function tierLabel(score) {
  return score >= 70 ? "High" : score >= 40 ? "Medium" : "Low";
}

/** Extract YYYY-MM-DD from a "2026-04-14 10:32:05 UTC" timestamp string. */
function leadDate(lead) {
  return lead.processed_at.slice(0, 10);
}

/**
 * Apply all active filters to the currently loaded page of leads.
 * Filters: tier (High/Medium/Low), keyword search, and date range.
 */
function filteredLeads() {
  return state.leads.filter(lead => {
    // Tier filter
    if (state.filter !== "all" && tier(lead.lead_score) !== state.filter) return false;

    // Keyword search across key fields
    if (state.search) {
      const q = state.search.toLowerCase();
      const fields = [lead.name, lead.company_name, lead.industry, lead.job_title, lead.email];
      if (!fields.some(f => f.toLowerCase().includes(q))) return false;
    }

    // Date range filter on processed_at
    if (state.dateFrom || state.dateTo) {
      const d = leadDate(lead);
      if (state.dateFrom && d < state.dateFrom) return false;
      if (state.dateTo   && d > state.dateTo)   return false;
    }

    return true;
  });
}

// ── Render orchestrator ───────────────────────────────────────────────────────

function renderAll() {
  renderHeader();
  renderDatasource();
  renderStats();
  renderTable();
  renderPagination();
}

// ── Header ────────────────────────────────────────────────────────────────────

function renderHeader() {
  const latest = state.leads.reduce((a, b) =>
    a.processed_at > b.processed_at ? a : b, { processed_at: "" }
  ).processed_at;
  document.getElementById("sync-badge").textContent =
    latest ? `Live · last entry ${latest}` : "Live · Google Sheets";
}

// ── Data source info bar ──────────────────────────────────────────────────────

function renderDatasource() {
  // Truncate the spreadsheet ID for display: first 8 chars + … + last 4
  const id = CONFIG.SPREADSHEET_ID;
  const idDisplay = id.length > 16
    ? id.slice(0, 8) + "…" + id.slice(-4)
    : id;

  const statusConfig = {
    idle:    { cls: "",       text: "—" },
    loading: { cls: "ds-spin", text: "⟳ Fetching…" },
    ok:      { cls: "ds-ok",  text: "✓ Synced" },
    error:   { cls: "ds-err", text: "✗ Error — " + state.fetchError },
  };
  const s = statusConfig[state.fetchStatus] ?? statusConfig.idle;

  document.getElementById("ds-sheet").textContent   = CONFIG.SHEET_NAME;
  document.getElementById("ds-id").textContent      = idDisplay;
  document.getElementById("ds-rows").textContent    = state.totalRows > 0 ? `${state.totalRows} rows` : "—";
  document.getElementById("ds-fetched").textContent = state.lastFetched
    ? state.lastFetched.toLocaleTimeString()
    : "—";

  const statusEl = document.getElementById("ds-status");
  statusEl.textContent = s.text;
  statusEl.className   = `ds-value ${s.cls}`;
}

// ── Stats cards ───────────────────────────────────────────────────────────────

function renderStats() {
  const leads = filteredLeads();
  const n     = leads.length;
  const high  = leads.filter(l => l.lead_score >= 70).length;
  const mid   = leads.filter(l => l.lead_score >= 40 && l.lead_score < 70).length;
  const low   = leads.filter(l => l.lead_score < 40).length;
  const avg   = n ? (leads.reduce((s, l) => s + l.lead_score, 0) / n).toFixed(1) : "—";

  document.getElementById("stats").innerHTML = `
    <div class="stat-card">
      <div class="label">Total in Sheet</div>
      <div class="value">${state.totalRows}</div>
      <div class="sub">all pages</div>
    </div>
    <div class="stat-card">
      <div class="label">Avg Score</div>
      <div class="value">${avg}</div>
      <div class="sub">this page</div>
    </div>
    <div class="stat-card high">
      <div class="label">High</div>
      <div class="value">${high}</div>
      <div class="sub">score ≥ 70</div>
    </div>
    <div class="stat-card mid">
      <div class="label">Medium</div>
      <div class="value">${mid}</div>
      <div class="sub">score 40–69</div>
    </div>
    <div class="stat-card low">
      <div class="label">Low</div>
      <div class="value">${low}</div>
      <div class="sub">score &lt; 40</div>
    </div>
  `;
}

// ── Table ─────────────────────────────────────────────────────────────────────

function renderTable() {
  const leads = filteredLeads();
  const tbody = document.getElementById("table-body");
  const empty = document.getElementById("empty");

  const pageStart = (state.page - 1) * PAGE_SIZE + 1;
  const pageEnd   = Math.min(state.page * PAGE_SIZE, state.totalRows);
  document.getElementById("count-label").textContent =
    `${leads.length} shown · rows ${pageStart}–${pageEnd} of ${state.totalRows}`;

  if (leads.length === 0) {
    tbody.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";

  tbody.innerHTML = leads.map(lead => {
    const t   = tier(lead.lead_score);
    const idx = state.leads.indexOf(lead);
    return `
      <tr onclick="openModal(${idx})">
        <td class="name"><span class="tier-dot ${t}"></span>${esc(lead.name)}</td>
        <td class="company">${esc(lead.company_name)}</td>
        <td class="title">${esc(lead.job_title)}</td>
        <td class="industry"><span class="badge">${esc(lead.industry)}</span></td>
        <td class="score-cell">
          <div class="score-pill ${t}">
            <span class="num">${lead.lead_score}</span>
            <div class="bar"><div class="bar-fill" style="width:${lead.lead_score}%"></div></div>
          </div>
        </td>
        <td class="action">${esc(lead.recommended_action)}</td>
      </tr>`;
  }).join("");
}

// ── Pagination ────────────────────────────────────────────────────────────────

function renderPagination() {
  const totalPages = Math.ceil(state.totalRows / PAGE_SIZE) || 1;
  const pg         = document.getElementById("pagination");

  // Hide pagination when there's only one page
  if (totalPages <= 1) { pg.style.display = "none"; return; }
  pg.style.display = "flex";

  const startRow = (state.page - 1) * PAGE_SIZE + 1;
  const endRow   = Math.min(state.page * PAGE_SIZE, state.totalRows);
  document.getElementById("page-info").textContent =
    `Rows ${startRow}–${endRow} of ${state.totalRows}  ·  Page ${state.page} of ${totalPages}`;

  document.getElementById("page-buttons").innerHTML =
    buildPageButtons(state.page, totalPages);
}

/**
 * Build HTML for the pagination button strip.
 * Shows: ← Prev  1 … 4 5 6 … 12  Next →
 */
function buildPageButtons(current, total) {
  const pages  = resolvePageNumbers(current, total);
  let   html   = "";

  // Prev
  html += `<button class="page-btn wide" onclick="loadPage(${current - 1})"
    ${current === 1 ? "disabled" : ""}>← Prev</button>`;

  // Numbered pages with ellipsis
  for (const p of pages) {
    if (p === "…") {
      html += `<span class="page-ellipsis">…</span>`;
    } else {
      html += `<button class="page-btn ${p === current ? "active" : ""}"
        onclick="loadPage(${p})">${p}</button>`;
    }
  }

  // Next
  html += `<button class="page-btn wide" onclick="loadPage(${current + 1})"
    ${current === total ? "disabled" : ""}>Next →</button>`;

  return html;
}

/**
 * Compute which page numbers (and where to insert "…") to show.
 * Always shows first, last, and a window of 2 around the current page.
 */
function resolvePageNumbers(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

  const visible = new Set([1, total]);
  for (let i = Math.max(2, current - 2); i <= Math.min(total - 1, current + 2); i++) {
    visible.add(i);
  }

  const sorted = [...visible].sort((a, b) => a - b);
  const result = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) result.push("…");
    result.push(p);
    prev = p;
  }
  return result;
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal(index) {
  const lead = state.leads[index];
  if (!lead) return;
  const t  = tier(lead.lead_score);
  const tl = tierLabel(lead.lead_score);

  document.getElementById("modal-content").innerHTML = `
    <div class="modal-header">
      <div class="name">${esc(lead.name)}</div>
      <div class="meta">${esc(lead.job_title)} &nbsp;·&nbsp; ${esc(lead.company_name)} &nbsp;·&nbsp; ${esc(lead.email)}</div>
    </div>

    <div class="modal-score-row ${t}">
      <div class="modal-score-num">${lead.lead_score}</div>
      <div class="progress-outer">
        <div class="progress-inner" style="width:${lead.lead_score}%"></div>
      </div>
      <div class="modal-score-meta">
        <div class="tier">${tl} Quality</div>
        <div class="industry-tag">${esc(lead.industry)}</div>
      </div>
    </div>

    <div class="modal-section">
      <div class="sec-label">Lead Message</div>
      <div class="message-box">"${esc(lead.message)}"</div>
    </div>

    <hr class="modal-divider" />

    <div class="modal-section">
      <div class="sec-label">Identified Business Need</div>
      <div class="sec-val">${esc(lead.business_need)}</div>
    </div>

    <div class="modal-section">
      <div class="sec-label">Recommended Action</div>
      <div class="action-box">→ ${esc(lead.recommended_action)}</div>
    </div>

    <div class="modal-footer">Processed at ${esc(lead.processed_at)}</div>
  `;

  document.getElementById("modal-overlay").classList.add("open");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.remove("open");
}

document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", e => {
  if (e.target === document.getElementById("modal-overlay")) closeModal();
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeModal();
});

// ── UI helpers ────────────────────────────────────────────────────────────────

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function setLoading(on) {
  document.getElementById("loading-overlay").classList.toggle("visible", on);
}

function showError(message) {
  document.getElementById("loading-overlay").classList.add("visible");
  document.getElementById("loading-overlay").innerHTML = `
    <div class="config-error">
      <h3>Failed to load data</h3>
      <p>${esc(message)}</p>
      <p style="margin-top:10px;font-size:.8rem">
        Check: API key is valid · Sheet is shared as "Anyone with link can view" · Sheets API is enabled
      </p>
      <button onclick="location.reload()" style="
        margin-top:16px; padding:8px 18px; border-radius:7px;
        border:1px solid var(--accent); background:var(--accent-bg);
        color:#a5b4fc; cursor:pointer; font-size:.85rem;">
        Retry
      </button>
    </div>`;
}

// ── Event listeners ───────────────────────────────────────────────────────────

document.getElementById("search").addEventListener("input", e => {
  state.search = e.target.value;
  renderAll();
});

document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.filter = btn.dataset.filter;
    renderAll();
  });
});

document.getElementById("date-from").addEventListener("change", e => {
  state.dateFrom = e.target.value;
  // Enforce: dateFrom cannot exceed dateTo
  if (state.dateTo && state.dateFrom > state.dateTo) {
    state.dateTo = state.dateFrom;
    document.getElementById("date-to").value = state.dateFrom;
  }
  renderAll();
});

document.getElementById("date-to").addEventListener("change", e => {
  state.dateTo = e.target.value;
  // Enforce: dateTo cannot be before dateFrom
  if (state.dateFrom && state.dateTo < state.dateFrom) {
    state.dateFrom = state.dateTo;
    document.getElementById("date-from").value = state.dateTo;
  }
  renderAll();
});

document.getElementById("clear-dates").addEventListener("click", () => {
  state.dateFrom = "";
  state.dateTo   = "";
  document.getElementById("date-from").value = "";
  document.getElementById("date-to").value   = "";
  renderAll();
});

// ── Bootstrap ─────────────────────────────────────────────────────────────────
// Pre-fill date inputs with today so the filter is active from the first load
document.getElementById("date-from").value = TODAY;
document.getElementById("date-to").value   = TODAY;
loadPage(1);
