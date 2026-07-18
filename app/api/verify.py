from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["verify"])

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SkillFlow · Data Verification</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         margin: 0; background: #0f1220; color: #e7e9f3; }
  header { padding: 18px 24px; background: #171a2e; border-bottom: 1px solid #2a2f4a;
           display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  header h1 { font-size: 18px; margin: 0; font-weight: 650; }
  .tag { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #2a2f4a; color: #aeb4d6; }
  main { max-width: 1000px; margin: 0 auto; padding: 24px; }
  .card { background: #171a2e; border: 1px solid #2a2f4a; border-radius: 12px; padding: 18px; margin-bottom: 18px; }
  .card h2 { margin: 0 0 12px; font-size: 15px; color: #c7ccf0; }
  label { display: block; font-size: 12px; color: #9aa0c4; margin: 10px 0 4px; }
  input, select { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid #2a2f4a;
                  background: #0f1220; color: #e7e9f3; font-size: 14px; }
  .row { display: flex; gap: 10px; flex-wrap: wrap; }
  .row > * { flex: 1; min-width: 140px; }
  button { cursor: pointer; border: 0; border-radius: 8px; padding: 10px 16px; font-size: 14px;
           font-weight: 600; background: #4f6bd8; color: white; margin-top: 12px; }
  button.secondary { background: #2a2f4a; color: #cdd2f0; }
  button:hover { filter: brightness(1.08); }
  .muted { color: #8b91b8; font-size: 13px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
  .kv { background: #0f1220; border: 1px solid #2a2f4a; border-radius: 8px; padding: 10px; }
  .kv .k { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #8b91b8; }
  .kv .v { font-size: 15px; font-weight: 600; margin-top: 3px; word-break: break-word; }
  .pill { display: inline-block; font-size: 12px; padding: 3px 9px; border-radius: 999px; margin: 2px 4px 2px 0; }
  .pill.good { background: #16351f; color: #7fe0a0; }
  .pill.bad { background: #3a1c22; color: #f2a0ad; }
  .pill.info { background: #1c2a44; color: #93b4f0; }
  .fresher-card { border-left: 3px solid #4f6bd8; }
  pre { background: #0b0e1a; border: 1px solid #2a2f4a; border-radius: 8px; padding: 12px;
        overflow-x: auto; font-size: 12px; color: #b8bee0; max-height: 320px; }
  .err { color: #f2a0ad; font-size: 13px; margin-top: 8px; }
  .ok { color: #7fe0a0; font-size: 13px; margin-top: 8px; }
  a { color: #93b4f0; }
  .hidden { display: none; }
</style>
</head>
<body>
<header>
  <h1>SkillFlow · Data Verification</h1>
  <span class="tag">read-only</span>
  <span class="tag" id="who">not logged in</span>
  <span style="flex:1"></span>
  <a href="/docs" target="_blank" class="muted">Open API docs ↗</a>
</header>
<main>
  <div class="card" id="loginCard">
    <h2>Sign in</h2>
    <p class="muted">Use the seeded demo accounts (password <code>Demo@123</code>), or type any account.</p>
    <label>Email</label>
    <input id="email" value="pm@skillflow.local">
    <label>Password</label>
    <input id="password" type="password" value="Demo@123">
    <div class="row">
      <button onclick="login()">Sign in</button>
      <button class="secondary" onclick="quick('pm@skillflow.local')">Demo PM</button>
      <button class="secondary" onclick="quick('fresher@skillflow.local')">Demo Fresher</button>
    </div>
    <div id="loginMsg"></div>
  </div>

  <div id="app" class="hidden">
    <div class="card">
      <div class="row">
        <button class="secondary" onclick="refresh()">↻ Refresh</button>
        <button class="secondary" onclick="logout()">Log out</button>
      </div>
    </div>
    <div id="content"></div>
  </div>
</main>

<script>
let token = localStorage.getItem("sf_token") || "";
let me = null;

function h(s){ return (s==null?"":String(s)).replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

async function api(path){
  const r = await fetch(path, { headers: token ? { Authorization: "Bearer " + token } : {} });
  if(!r.ok){ throw new Error(path + " → HTTP " + r.status); }
  return r.json();
}

function quick(email){
  document.getElementById("email").value = email;
  document.getElementById("password").value = "Demo@123";
  login();
}

async function login(){
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const msg = document.getElementById("loginMsg");
  msg.className = ""; msg.textContent = "Signing in…";
  try{
    const r = await fetch("/api/auth/login", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ email, password })
    });
    if(!r.ok){ throw new Error("Login failed (HTTP " + r.status + ")"); }
    const data = await r.json();
    token = data.access_token; localStorage.setItem("sf_token", token);
    msg.className = "ok"; msg.textContent = "Signed in.";
    await afterLogin();
  }catch(e){ msg.className = "err"; msg.textContent = e.message; }
}

function logout(){
  token = ""; me = null; localStorage.removeItem("sf_token");
  document.getElementById("app").classList.add("hidden");
  document.getElementById("loginCard").classList.remove("hidden");
  document.getElementById("who").textContent = "not logged in";
}

async function afterLogin(){
  me = await api("/api/auth/me");
  document.getElementById("who").textContent = me.name + " · " + me.role;
  document.getElementById("loginCard").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  await refresh();
}

async function refresh(){
  const c = document.getElementById("content");
  c.innerHTML = "<p class='muted'>Loading…</p>";
  try{
    if(me.role === "PM"){ c.innerHTML = await renderPM(); }
    else { c.innerHTML = await renderFresher(); }
  }catch(e){ c.innerHTML = "<div class='card'><div class='err'>"+h(e.message)+"</div></div>"; }
}

function kv(k,v){ return "<div class='kv'><div class='k'>"+h(k)+"</div><div class='v'>"+h(v)+"</div></div>"; }
function pills(arr, cls){ if(!arr||!arr.length) return "<span class='muted'>—</span>";
  return arr.map(x=>"<span class='pill "+cls+"'>"+h(typeof x==="object"?JSON.stringify(x):x)+"</span>").join(""); }

async function renderPM(){
  const d = await api("/api/pm/dashboard");
  let html = "<div class='card'><h2>Team summary</h2><div class='grid'>"
    + kv("Assigned freshers", d.summary.assigned_freshers)
    + kv("Need human interaction", d.summary.freshers_needing_interaction)
    + kv("Reports this week", d.summary.reports_received_this_week)
    + "</div></div>";
  for(const f of d.freshers){
    const t = f.current_assigned_task || {};
    html += "<div class='card fresher-card'>"
      + "<h2>"+h(f.fresher.name)+" <span class='muted'>· "+h(f.fresher.id)+"</span></h2>"
      + "<div class='grid'>"
      + kv("Roadmap progress", (f.roadmap_progress ?? 0) + "%")
      + kv("Latest score", f.latest_daily_report ? f.latest_daily_report.overall_score : "—")
      + kv("Strongest skill", f.strongest_skill || "—")
      + kv("Current gap", f.current_gap || "—")
      + kv("Next focus", f.next_learning_focus || "—")
      + kv("Mentor required", f.mentor_required ? "YES" : "no")
      + "</div>"
      + "<label>Verified skills</label>" + pills(f.strengths, "good")
      + "<label>Weak areas</label>" + pills(f.weaknesses, "bad")
      + "<label>Evidence</label>" + pills(f.evidence, "info")
      + "<label>Current assigned task</label><div class='muted'>"
        + h(t.task_id||"—") + " — " + h(t.task_title||"") + "</div>"
      + "<label>Reports on file</label><div class='muted'>daily: "
        + (f.latest_daily_report?"✓":"—") + " · weekly: " + (f.latest_weekly_report?"✓":"—")
        + " · final: " + (f.final_report?"✓":"—") + "</div>"
      + "</div>";
  }
  return html;
}

async function renderFresher(){
  const p = await api("/api/freshers/me/profile");
  let roadmap = null, reports = [];
  try { roadmap = await api("/api/freshers/me/roadmaps/current"); } catch(e){}
  try { reports = await api("/api/freshers/me/reports?limit=50"); } catch(e){}
  const t = (roadmap && roadmap.roadmap_payload && roadmap.roadmap_payload.current_task) || {};

  let html = "<div class='card'><h2>Profile</h2><div class='grid'>"
    + kv("Target role", p.target_role) + kv("Joining date", p.joining_date)
    + kv("Current roadmap", p.current_roadmap_id ? "set" : "none") + "</div>"
    + "<label>Profile metadata</label><pre>"+h(JSON.stringify(p.profile_metadata,null,2))+"</pre></div>";

  html += "<div class='card'><h2>Current roadmap</h2>";
  if(roadmap){
    html += "<div class='grid'>" + kv("Title", roadmap.title) + kv("Version", roadmap.version)
      + kv("Status", roadmap.status) + kv("Completion", (roadmap.completion_pct||0)+"%") + "</div>"
      + "<label>Current task ("+h(t.task_id||"—")+")</label><div class='muted'>"+h(t.task_title||"")+"</div>"
      + "<label>Acceptance criteria</label>" + pills(t.acceptance_criteria, "info")
      + "<label>Evaluation criteria</label>" + pills(t.evaluation_criteria, "info");
  } else { html += "<p class='muted'>No current roadmap.</p>"; }
  html += "</div>";

  html += "<div class='card'><h2>Reports ("+reports.length+")</h2>";
  if(!reports.length){ html += "<p class='muted'>None yet.</p>"; }
  for(const r of reports){
    const ev = (r.report_payload && r.report_payload.evaluation) || {};
    html += "<div class='kv' style='margin-bottom:10px'>"
      + "<div class='k'>"+h(r.report_type)+" · "+h(r.report_date||r.period_end||"")+" · score "+h(r.overall_score)+"</div>"
      + "<div style='margin-top:6px'>" + pills(ev.verified_skills, "good") + pills(ev.weak_areas, "bad") + "</div>"
      + (ev.criteria_source ? "<div class='muted' style='margin-top:6px'>criteria_source: "+h(ev.criteria_source)+"</div>" : "")
      + "</div>";
  }
  html += "</div>";
  return html;
}

if(token){ afterLogin().catch(()=>logout()); }
</script>
</body>
</html>"""


@router.get("/verify", response_class=HTMLResponse)
def verify_page():
    return HTMLResponse(content=PAGE)
