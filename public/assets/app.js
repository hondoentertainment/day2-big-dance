let lastPayload = null;

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return iso;
  }
}

function el(tag, attrs, children) {
  const n = document.createElement(tag);
  if (attrs) {
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k === "html") n.innerHTML = v;
      else n.setAttribute(k, v);
    });
  }
  (children || []).forEach((c) => {
    if (c) n.appendChild(c);
  });
  return n;
}

function pickRow(p, full) {
  const tr = document.createElement("tr");
  const roleLabel = p.pick_role === "home" ? "Home" : "Away";
  const badges = [el("span", { class: `badge role-${p.pick_role || "away"}`, text: roleLabel })];
  if (!p.ratings_ok) {
    badges.push(el("span", { class: "badge market-only", text: "Market-only" }));
  }
  const pickCell = el("td", null, []);
  pickCell.appendChild(document.createTextNode(p.pick_team || "—"));
  badges.forEach((b) => pickCell.appendChild(b));

  const matchup = `${p.away_team || ""} @ ${p.home_team || ""}`;

  if (!full) {
    tr.appendChild(el("td", { class: "num", text: String(p.rank ?? "") }));
    tr.appendChild(pickCell);
    tr.appendChild(el("td", { class: "num", text: p.line_display || "—" }));
    tr.appendChild(el("td", { text: matchup }));
    tr.appendChild(el("td", { class: "num", text: fmtTime(p.commence_time) }));
    tr.appendChild(
      el("td", { class: "num", text: p.confidence_pct != null ? String(p.confidence_pct) : "—" }),
    );
    tr.appendChild(el("td", { class: "num", text: p.p_blend != null ? String(p.p_blend) : "—" }));
    const dataLabel = p.ratings_ok ? "Ratings + market" : "Market only";
    tr.appendChild(el("td", { text: dataLabel }));
    return tr;
  }

  tr.appendChild(el("td", { class: "num", text: String(p.rank ?? "") }));
  tr.appendChild(pickCell);
  tr.appendChild(el("td", { class: "num", text: p.line_display || "—" }));
  tr.appendChild(el("td", { text: matchup }));
  tr.appendChild(
    el("td", { class: "num", text: p.confidence_pct != null ? String(p.confidence_pct) : "—" }),
  );
  tr.appendChild(el("td", { text: p.notes || "—" }));
  return tr;
}

function renderPickCard(p) {
  const card = el("article", { class: "pick-card" });
  card.appendChild(el("div", { class: "rank", text: `Rank ${p.rank ?? "—"}` }));
  card.appendChild(el("div", { class: "pick-name", text: p.pick_team || "—" }));
  card.appendChild(el("div", { class: "line", text: p.line_display || "—" }));
  const sub = `${p.away_team || ""} @ ${p.home_team || ""} · ${fmtTime(p.commence_time)}`;
  card.appendChild(el("div", { class: "meta-line", text: sub }));
  const conf =
    p.confidence_pct != null ? `Confidence index: ${p.confidence_pct}` : "Confidence index: —";
  card.appendChild(el("div", { class: "meta-line", text: conf }));
  const badges = el("div", { class: "badges" });
  badges.appendChild(el("span", { class: `badge role-${p.pick_role || "away"}`, text: p.pick_role === "home" ? "Home" : "Away" }));
  if (!p.ratings_ok) {
    badges.appendChild(el("span", { class: "badge market-only", text: "Market-only" }));
  }
  card.appendChild(badges);
  return card;
}

function renderCards(container, picks) {
  container.innerHTML = "";
  picks.forEach((p) => container.appendChild(renderPickCard(p)));
}

function renderPrintBlock(topPicks, generatedAt) {
  const block = document.getElementById("print-top16");
  block.innerHTML = "";
  const h = el("h2", { text: "Top 16 ATS picks" });
  block.appendChild(h);
  if (generatedAt) {
    block.appendChild(el("p", { text: `Generated: ${generatedAt}` }));
  }
  const ol = document.createElement("ol");
  topPicks.forEach((p) => {
    const li = el("li", {
      text: `${p.line_display || p.pick_team} — ${p.away_team} @ ${p.home_team} (conf. ${p.confidence_pct ?? "—"})`,
    });
    ol.appendChild(li);
  });
  block.appendChild(ol);
}

function renderLastUpdated(meta) {
  const lu = document.getElementById("last-updated");
  const gen = meta.generated_at ? fmtTime(meta.generated_at) : null;
  const parts = [];
  if (gen) parts.push(`Last updated: ${gen}`);
  if (meta.cache_layer) parts.push(`Source: ${meta.cache_layer}`);
  if (meta.cache_ttl_seconds != null && meta.cache_ttl_seconds > 0) {
    parts.push(`Cache TTL ${meta.cache_ttl_seconds}s`);
  }
  lu.textContent = parts.join(" · ");
}

function renderMeta(meta) {
  renderLastUpdated(meta);
  const sec = document.getElementById("meta-section");
  sec.classList.remove("hidden");
  sec.innerHTML = "";
  sec.appendChild(el("h2", { text: "Run info" }));
  const dl = document.createElement("dl");
  const rows = [
    ["Generated at (UTC)", meta.generated_at],
    ["Target date", meta.target_date],
    ["Timezone", meta.timezone],
    ["Events on date", meta.events_on_date],
    ["API requests remaining", meta.remaining_requests],
    ["Served from", meta.served_from],
    ["Cache layer", meta.cache_layer],
    ["Run snapshot", meta.run_saved_as],
    ["Live error", meta.live_error],
    ["Ratings file", meta.ratings_loaded ? "Loaded" : "Missing or empty"],
  ];
  rows.forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    dl.appendChild(el("dt", { text: k }));
    dl.appendChild(el("dd", { text: String(v) }));
  });
  sec.appendChild(dl);
}

function renderAlert(msg, isError) {
  const sec = document.getElementById("alert-section");
  if (!msg) {
    sec.classList.add("hidden");
    sec.innerHTML = "";
    return;
  }
  sec.classList.remove("hidden");
  sec.classList.toggle("error", !!isError);
  sec.textContent = msg;
}

function top16Text(picks) {
  const lines = picks.map(
    (p) =>
      `${p.rank}. ${p.line_display || p.pick_team} | ${p.away_team} @ ${p.home_team} | conf ${p.confidence_pct ?? "—"}`,
  );
  return lines.join("\n");
}

async function copyTop16() {
  const status = document.getElementById("status");
  if (!lastPayload || !lastPayload.picks || !lastPayload.picks.length) {
    status.textContent = "Nothing to copy yet.";
    return;
  }
  const top = lastPayload.picks.slice(0, 16);
  const text = top16Text(top);
  try {
    await navigator.clipboard.writeText(text);
    status.textContent = "Copied top 16 to clipboard.";
  } catch {
    status.textContent = "Clipboard blocked — select and copy manually.";
  }
}

function doPrint() {
  if (!lastPayload || !lastPayload.picks || !lastPayload.picks.length) return;
  const top = lastPayload.picks.slice(0, 16);
  renderPrintBlock(top, lastPayload.meta?.generated_at || "");
  window.print();
}

async function fetchPicks(url, options) {
  const r = await fetch(url, options);
  const ct = r.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    const t = await r.text();
    throw new Error(t.slice(0, 200) || `HTTP ${r.status}`);
  }
  const data = await r.json();
  if (!r.ok) {
    let detail = data.detail ?? data.message ?? data;
    if (Array.isArray(detail)) {
      detail = detail.map((x) => (typeof x === "object" && x.msg ? x.msg : JSON.stringify(x))).join("; ");
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function applyPicksData(data) {
  lastPayload = data;
  const meta = data.meta || {};
  renderMeta(meta);

  const status = document.getElementById("status");
  if (meta.served_from && meta.served_from !== "the-odds-api") {
    status.textContent = `Showing file/example fallback (${meta.served_from}).`;
  } else if (meta.remaining_requests != null) {
    status.textContent = `Odds API requests remaining: ${meta.remaining_requests}`;
  } else {
    status.textContent = "";
  }

  const err = meta.error || meta.live_error;
  if (err && (!data.picks || data.picks.length === 0)) {
    renderAlert(err, true);
  } else if (err) {
    renderAlert(`Note: ${err}`, false);
  } else {
    renderAlert("", false);
  }

  const body = document.getElementById("picks-body");
  const allBody = document.getElementById("picks-all-body");
  const cards = document.getElementById("mobile-cards-top16");
  body.innerHTML = "";
  allBody.innerHTML = "";

  const picks = data.picks || [];
  if (!picks.length) {
    body.appendChild(
      el("tr", null, [
        el("td", {
          colspan: "8",
          class: "empty",
          text: "No picks for this date. Set ODDS_API_KEY, check TARGET_DATE / TIMEZONE, or use Refresh live odds.",
        }),
      ]),
    );
    cards.innerHTML = "";
    return;
  }

  const top = picks.slice(0, 16);
  renderCards(cards, top);
  top.forEach((p) => body.appendChild(pickRow(p, false)));
  picks.forEach((p) => allBody.appendChild(pickRow(p, true)));
  renderPrintBlock(top, meta.generated_at || "");
}

async function loadPicks() {
  const status = document.getElementById("status");
  const body = document.getElementById("picks-body");
  status.textContent = "Loading…";
  body.innerHTML = "";
  body.appendChild(el("tr", null, [el("td", { colspan: "8", class: "loading", text: "Loading picks…" })]));

  try {
    const data = await fetchPicks("/api/picks");
    applyPicksData(data);
  } catch (e) {
    status.textContent = "";
    body.innerHTML = "";
    body.appendChild(
      el("tr", null, [
        el("td", {
          colspan: "8",
          class: "empty",
          text: "Could not reach the server. Run python run_server.py from the project folder.",
        }),
      ]),
    );
    renderAlert(String(e), true);
  }
}

async function refreshLive() {
  const status = document.getElementById("status");
  const secret = document.getElementById("refresh-secret").value.trim();
  const headers = { Accept: "application/json" };
  if (secret) headers["X-Refresh-Secret"] = secret;
  status.textContent = "Refreshing live odds…";
  try {
    const data = await fetchPicks("/api/picks/refresh", { method: "POST", headers });
    applyPicksData(data);
    status.textContent = "Live refresh complete.";
  } catch (e) {
    status.textContent = "";
    renderAlert(String(e), true);
  }
}

document.getElementById("btn-refresh").addEventListener("click", () => refreshLive());
document.getElementById("btn-copy").addEventListener("click", () => copyTop16());
document.getElementById("btn-print").addEventListener("click", () => doPrint());

loadPicks();
