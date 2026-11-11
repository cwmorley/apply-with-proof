const EXAMPLE = {
  profile: {
    name: "Alex Morgan",
    headline: "Product and commercial systems builder",
    summary: "Cross-functional operator who turns ambiguous product, marketing, and operating problems into practical systems and measurable progress.",
    contact: { email: "alex@example.com", phone: "555-0100", location: "Anytown, ST", linkedin: "linkedin.com/in/alexmorgan" },
    skills: ["product marketing", "go-to-market", "CRM", "automation", "customer discovery", "analytics", "stakeholder leadership"],
    experiences: [
      { company: "Example Systems Co.", title: "Founder & Principal", dates: "2020–Present", bullets: ["Built go-to-market and business systems for technology and services clients.", "Designed CRM and automation workflows that connected lead capture, follow-up, and reporting.", "Translated customer discovery and market research into positioning, offers, and launch plans."] },
      { company: "Example Technology Co.", title: "Senior Product Marketing Manager", dates: "2016–2020", bullets: ["Led cross-functional product marketing across product, sales, channel, and communications teams.", "Developed competitive analysis, sales enablement, and customer-facing messaging for new launches."] }
    ]
  },
  narrative: "I am strongest when a problem crosses boundaries. I can move from customer language to product direction, from product direction to a commercial story, and from the story to the systems that make it executable.\n\nI consolidated seven CRM and automation workflows for one client. The work improved follow-up consistency and reduced manual handoffs, although the response-time improvement was estimated rather than formally measured.\n\nI built a product marketing launch operating model that connected customer discovery, positioning, sales enablement, and stakeholder decision-making. The model was useful, but the launch outcome should be verified before turning it into a quantified resume claim.\n\nI have often entered situations where the product, marketing, sales, and operations pieces were not yet connected. I enjoy creating the operating model, not just writing the launch copy.",
  job: "# Director of Product Marketing\n\nWe are looking for a cross-functional product marketing leader to define positioning, guide go-to-market strategy, partner with product and sales, and turn customer and market insight into compelling launches.\n\nThe role requires strong stakeholder leadership, customer discovery, competitive analysis, messaging, sales enablement, analytics, and the ability to operate in an ambiguous environment."
};

let analysis = null;
let decisions = {};
let artifacts = null;

const $ = (id) => document.getElementById(id);

function save() {
  localStorage.setItem("cec-profile", $("profile").value);
  localStorage.setItem("cec-narrative", $("narrative").value);
  localStorage.setItem("cec-job", $("job").value);
  localStorage.setItem("cec-resume", $("resume-text").value);
  localStorage.setItem("cec-job-url", $("job-url").value);
  $("save-status").textContent = "Saved in this browser";
}

function loadExample() {
  $("profile").value = JSON.stringify(EXAMPLE.profile, null, 2);
  $("narrative").value = EXAMPLE.narrative;
  $("job").value = EXAMPLE.job;
  $("resume-text").value = "Alex Morgan\nProduct and commercial systems builder\n\nExperience\nSkills\nEducation";
  save();
}

function restore() {
  const profile = localStorage.getItem("cec-profile");
  if (profile) {
    $("profile").value = profile;
    $("narrative").value = localStorage.getItem("cec-narrative") || "";
    $("job").value = localStorage.getItem("cec-job") || "";
    $("resume-text").value = localStorage.getItem("cec-resume") || "";
    $("job-url").value = localStorage.getItem("cec-job-url") || "";
  } else loadExample();
}

async function readFileInto(file, target, statusId) {
  if (!file) return;
  try {
    $(statusId).textContent = `Reading ${file.name} locally…`;
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunk = 0x8000;
    for (let index = 0; index < bytes.length; index += chunk) binary += String.fromCharCode(...bytes.subarray(index, index + chunk));
    const result = await post("/api/parse-document", { filename: file.name, data: btoa(binary) });
    $(target).value = target === "narrative" && $(target).value.trim() ? `${$(target).value.trim()}\n\n${result.text}` : result.text;
    save();
    $(statusId).textContent = `Loaded ${file.name} · ${result.characters.toLocaleString()} characters`;
  } catch (error) {
    $(statusId).textContent = error.message;
  }
}

async function fetchJob() {
  const url = $("job-url").value.trim();
  if (!url) { $("job-url-status").textContent = "Paste a public job URL first."; return; }
  try {
    $("fetch-job").disabled = true;
    $("job-url-status").textContent = "Fetching and extracting page text locally…";
    const result = await post("/api/fetch-job", { url });
    $("job").value = result.text;
    save();
    $("job-url-status").textContent = `${result.title || "Page loaded"} · ${result.text.length.toLocaleString()} characters${result.warnings.length ? " · " + result.warnings[0] : ""}`;
  } catch (error) { $("job-url-status").textContent = error.message; }
  finally { $("fetch-job").disabled = false; }
}

function profilePayload() {
  try { return JSON.parse($("profile").value || "{}"); }
  catch (error) { throw new Error("Master profile is not valid JSON: " + error.message); }
}

async function post(path, payload) {
  const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  const body = await response.json();
  if (!response.ok || body.error) throw new Error(body.error || "Request failed");
  return body;
}

function renderAnalysis() {
  $("empty-state").classList.add("hidden");
  $("result-state").classList.remove("hidden");
  $("recommendation").textContent = analysis.recommendation;
  $("fit-note").textContent = analysis.fit_note;
  $("coverage").innerHTML = `${Math.round(analysis.coverage * 100)}%<small>evidence coverage</small>`;
  $("metrics").innerHTML = [
    [analysis.job_terms.length, "role terms identified"],
    [analysis.approved_matches.length, "approved matches"],
    [analysis.candidate_evidence.length, "review cards"],
  ].map(([value, label]) => `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`).join("");
  $("approved-count").textContent = `${analysis.approved_matches.length} matches`;
  $("approved-list").innerHTML = analysis.approved_matches.length ? analysis.approved_matches.map(item => `<div class="evidence-card"><div class="claim">${escapeHtml(item.claim)}</div><div class="source">${escapeHtml(item.source)}</div><div>${item.matched_terms.map(term => `<span class="term">${escapeHtml(term)}</span>`).join("")}</div></div>`).join("") : `<p class="muted">No approved profile evidence matched yet. Review the gaps before generating.</p>`;
  $("candidate-count").textContent = `${analysis.candidate_evidence.length} surfaced`;
  $("candidate-list").innerHTML = analysis.candidate_evidence.length ? analysis.candidate_evidence.map(card => candidateCard(card)).join("") : `<p class="muted">No narrative expansion cards surfaced for this role.</p>`;
  $("missing-list").innerHTML = analysis.missing_terms.length ? analysis.missing_terms.map(term => `<span>${escapeHtml(term)}</span>`).join("") : `<span class="term">No obvious gaps from this deterministic pass</span>`;
  const ats = analysis.ats_report;
  $("ats-label").textContent = `${ats.label} · ${ats.checks_passed}/${ats.checks_total}`;
  $("ats-disclaimer").textContent = ats.disclaimer;
  $("ats-list").innerHTML = ats.checks.map(item => `<div class="check ${item.passed ? "" : "fail"}"><span class="mark">${item.passed ? "✓" : "!"}</span><div><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.detail)}</small></div></div>`).join("");
  $("artifacts").classList.add("hidden");
  artifacts = null;
}

function candidateCard(card) {
  const selected = decisions[card.id] || "";
  return `<div class="evidence-card candidate"><div class="claim">${escapeHtml(card.claim)}</div><div class="source">${escapeHtml(card.source)} · ${escapeHtml(card.confidence)} confidence</div><div>${card.matched_terms.map(term => `<span class="term">${escapeHtml(term)}</span>`).join("")}</div><div class="review-actions"><button class="${selected === "application_only" ? "selected" : ""}" onclick="decide('${card.id}', 'application_only')">Use this application</button><button class="${selected === "promote" ? "selected" : ""}" onclick="decide('${card.id}', 'promote')">Promote to master</button><button class="${selected === "context" ? "selected" : ""}" onclick="decide('${card.id}', 'context')">Context only</button><button class="reject ${selected === "reject" ? "selected" : ""}" onclick="decide('${card.id}', 'reject')">Reject</button></div></div>`;
}

window.decide = function(id, decision) {
  decisions[id] = decision;
  renderAnalysis();
};

async function analyze() {
  try {
    save();
    $("analyze").disabled = true;
    analysis = await post("/api/analyze", { profile: profilePayload(), narrative: $("narrative").value, job_description: $("job").value, resume_text: $("resume-text").value });
    decisions = {};
    renderAnalysis();
  } catch (error) { alert(error.message); }
  finally { $("analyze").disabled = false; }
}

async function generate() {
  try {
    $("generate").disabled = true;
    artifacts = await post("/api/generate", { profile: profilePayload(), narrative: $("narrative").value, job_description: $("job").value, analysis, decisions });
    renderArtifacts();
  } catch (error) { alert(error.message); }
  finally { $("generate").disabled = false; }
}

function renderArtifacts() {
  const entries = [["Resume", "resume"], ["Cover letter", "cover_letter"], ["Interview stories", "interview_stories"], ["Application answers", "application_answers"], ["ATS report", "ats_report"], ["Review ledger", "review_ledger"], ["Prompt pack", "prompt_pack"]];
  $("artifacts").classList.remove("hidden");
  $("artifacts").innerHTML = `<div class="artifact-tabs">${entries.map(([label, key], index) => `<button class="${index === 0 ? "active" : ""}" onclick="showArtifact('${key}', this)">${label}</button>`).join("")}</div><pre id="artifact-content"></pre>`;
  showArtifact("resume", $("artifacts").querySelector("button"));
}

window.showArtifact = function(key, button) {
  document.querySelectorAll(".artifact-tabs button").forEach(item => item.classList.remove("active"));
  if (button) button.classList.add("active");
  const value = artifacts[key];
  $("artifact-content").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
};

function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])); }

$("load-example").addEventListener("click", loadExample);
$("analyze").addEventListener("click", analyze);
$("generate").addEventListener("click", generate);
$("clear").addEventListener("click", () => { localStorage.clear(); analysis = null; decisions = {}; location.reload(); });
$("fetch-job").addEventListener("click", fetchJob);
$("resume-file").addEventListener("change", event => readFileInto(event.target.files[0], "resume-text", "resume-file-status"));
$("narrative-file").addEventListener("change", event => readFileInto(event.target.files[0], "narrative", "narrative-file-status"));
["profile", "narrative", "job", "resume-text", "job-url"].forEach(id => $(id).addEventListener("input", save));
restore();
