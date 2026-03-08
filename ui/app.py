"""PRD Forge Web UI — Read-only FastAPI application."""

import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    yield
    if pool:
        await pool.close()


app = FastAPI(title="PRD Forge UI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


def dt(v):
    if v is None:
        return None
    return v.isoformat() if hasattr(v, "isoformat") else str(v)


def row_dict(r):
    d = dict(r)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PRD Forge</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="/static/marked.min.js"></script>
<script src="/static/highlight.min.js"></script>
<link rel="stylesheet" href="/static/github-dark.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#2b2d35;--surface:#33353f;--secondary:#3c3e4a;--border:#44465a;--border-muted:#52546a;
  --text:#e2e4ea;--text-sec:#9496ad;--text-muted:#7a7c94;
  --accent:#6366f1;
  --approved:#10b981;--review:#f59e0b;--in_progress:#3b82f6;--draft:#7a7c94;--outdated:#ef4444;
  --notes-accent:#f59e0b;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);display:flex;height:100vh;overflow:hidden}
code,pre{font-family:'JetBrains Mono',monospace}

/* Sidebar */
.sidebar{width:360px;min-width:360px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
.sidebar-header{padding:16px;border-bottom:1px solid var(--border)}
.sidebar-header h1{font-size:18px;font-weight:700;margin-bottom:4px}
.sidebar-header .meta{font-size:12px;color:var(--text-sec)}
.sidebar-header select{width:100%;margin-top:8px;padding:6px 8px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:13px}
.sidebar-header .export-btn{display:inline-block;margin-top:8px;padding:4px 12px;background:var(--accent);color:#fff;border-radius:6px;font-size:12px;text-decoration:none;font-weight:500}
.tabs{display:flex;border-bottom:1px solid var(--border)}
.tab{flex:1;padding:8px;text-align:center;font-size:13px;font-weight:500;cursor:pointer;color:var(--text-sec);border-bottom:2px solid transparent;transition:all .15s}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab:hover{color:var(--text)}
.filters{padding:8px 12px;display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--border)}
.chip{padding:2px 8px;border-radius:12px;font-size:11px;cursor:pointer;border:1px solid var(--border);color:var(--text-sec);transition:all .15s}
.chip:hover,.chip.active{border-color:var(--accent);color:var(--accent)}
.section-list{flex:1;overflow-y:auto;padding:4px 0}
.section-item{padding:10px 16px;cursor:pointer;border-bottom:1px solid var(--border);transition:background .1s}
.section-item:hover{background:var(--secondary)}
.section-item.active{background:var(--secondary);border-left:3px solid var(--accent)}
.section-item .title{font-size:14px;font-weight:500;display:flex;align-items:center;gap:6px}
.section-item .meta-line{font-size:11px;color:var(--text-muted);margin-top:2px}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0}

/* Main Panel */
.main{flex:1;overflow-y:auto;padding:40px 56px;display:flex;justify-content:center}
.content-wrap{max-width:780px;width:100%}
.section-title{font-size:26px;font-weight:700;margin-bottom:8px;color:#f0f1f5}
.meta-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:16px;font-size:13px;color:var(--text-sec)}
.meta-row .badge{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;color:#fff}
.summary-box{padding:16px 20px;border:1px solid var(--border);border-radius:8px;margin-bottom:20px;font-size:15px;line-height:1.75;color:var(--text-sec);background:var(--surface)}
.notes-box{padding:16px 20px;border:1px solid var(--notes-accent);border-radius:8px;margin-bottom:20px;font-size:15px;line-height:1.75;background:rgba(245,158,11,0.08);color:#e8c060}
.notes-box .label{font-weight:600;margin-bottom:4px}
.tag-chip{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11px;background:var(--secondary);color:var(--text-sec);margin-right:4px}

/* Prose */
.prose{line-height:1.85;font-size:16px;color:var(--text)}
.prose h1,.prose h2,.prose h3{font-weight:600;color:#f0f1f5}
.prose h1{font-size:22px;margin:32px 0 12px}.prose h2{font-size:19px;margin:28px 0 10px}.prose h3{font-size:17px;margin:24px 0 8px}
.prose p{margin:12px 0}
.prose ul,.prose ol{margin:8px 0 20px 20px;color:var(--text-sec)}
.prose li{margin:8px 0;color:var(--text)}
.prose li::marker{color:var(--text-muted)}
.prose ul+p>strong:first-child,.prose ol+p>strong:first-child{display:inline-block;margin-top:8px}
.prose p>strong:only-child{display:block;margin-top:20px;font-size:17px;color:#f0f1f5}
.prose code{background:var(--secondary);padding:2px 6px;border-radius:4px;font-size:13px}
.prose pre{background:#252730;border:1px solid #44465a;border-radius:8px;padding:16px 20px;overflow-x:auto;margin:20px 0}
.prose pre code{background:none;padding:0;font-family:'JetBrains Mono',monospace;font-size:13px}
.prose table{width:100%;border-collapse:collapse;margin:16px 0}
.prose th,.prose td{padding:8px 12px;border:1px solid var(--border);text-align:left;font-size:13px}
.prose th{background:var(--surface);font-weight:600}
.prose blockquote{border-left:3px solid var(--accent);padding-left:12px;margin:16px 0;color:var(--text-sec)}
.prose strong{font-weight:600;color:#e8e9ed}
.prose a{color:var(--accent)}
.prose hr{border:none;border-top:1px solid var(--border);margin:24px 0}

/* Deps & Revisions */
.deps-panel{margin-top:24px;padding:16px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}
.deps-panel h3{font-size:14px;font-weight:600;margin-bottom:8px}
.dep-chip{display:inline-block;padding:4px 10px;margin:2px;border-radius:6px;font-size:12px;cursor:pointer;background:var(--secondary);color:var(--accent);border:1px solid var(--border);transition:all .15s}
.dep-chip:hover{border-color:var(--accent)}
.dep-type{font-size:10px;color:var(--text-muted);margin-left:4px}
.rev-table{width:100%;margin-top:8px;font-size:13px}
.rev-table th,.rev-table td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--border)}
.rev-table th{color:var(--text-sec);font-weight:500}

/* Changelog Tab */
.changelog-list{padding:8px 16px;overflow-y:auto;flex:1}
.cl-item{padding:8px 0;border-bottom:1px solid var(--border);font-size:13px}
.cl-item .cl-section{color:var(--accent);font-weight:500}
.cl-item .cl-desc{color:var(--text-sec)}
.cl-item .cl-time{color:var(--text-muted);font-size:11px}

/* Deps Graph Tab */
.deps-graph{padding:0;overflow-y:auto;flex:1;font-size:13px}
.deps-header{padding:16px 16px 12px;border-bottom:1px solid var(--border)}
.deps-header h3{font-size:14px;font-weight:600;color:#f0f1f5;margin-bottom:4px}
.deps-header p{font-size:12px;color:var(--text-muted)}
.dep-row{display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--border)}
.dep-row:hover{background:var(--secondary)}
.dep-from,.dep-to{font-size:13px;font-weight:500;color:var(--text);min-width:0;cursor:pointer}
.dep-from:hover,.dep-to:hover{color:var(--accent)}
.dep-arrow{color:var(--accent);font-size:14px;flex-shrink:0}
.dep-type{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;margin-left:auto;flex-shrink:0}
.dep-type-references{background:rgba(99,102,241,0.12);color:#818cf8}
.dep-type-implements{background:rgba(59,130,246,0.12);color:#60a5fa}
.dep-type-extends{background:rgba(16,185,129,0.12);color:#34d399}
.dep-type-blocks{background:rgba(239,68,68,0.12);color:#f87171}

/* Empty state */
.empty{display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:16px}

/* Tab content */
.tab-content{display:none;flex:1;overflow-y:auto}
.tab-content.active{display:flex;flex-direction:column}
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-header">
    <h1 id="projName">PRD Forge</h1>
    <div class="meta" id="projMeta"></div>
    <select id="projSelect" onchange="switchProject(this.value)"></select>
    <div style="display:flex;gap:8px;margin-top:8px">
      <a class="export-btn" id="exportBtn" href="#" download>Export</a>
      <a class="export-btn" href="#" onclick="loadFullPRD();return false" style="background:var(--secondary);border:1px solid var(--border)">View Full PRD</a>
    </div>
  </div>
  <div class="tabs">
    <div class="tab active" onclick="switchTab('sections')">Sections</div>
    <div class="tab" onclick="switchTab('changelog')">Changelog</div>
    <div class="tab" onclick="switchTab('deps')">Deps Graph</div>
  </div>
  <div class="tab-content active" id="tab-sections">
    <div class="filters" id="filters"></div>
    <div class="section-list" id="sectionList"></div>
  </div>
  <div class="tab-content" id="tab-changelog">
    <div class="changelog-list" id="changelogList"></div>
  </div>
  <div class="tab-content" id="tab-deps">
    <div class="deps-graph" id="depsGraph"></div>
  </div>
</div>
<div class="main">
  <div class="content-wrap" id="mainContent">
    <div class="empty">Select a section to view</div>
  </div>
</div>

<script>
const renderer=new marked.Renderer();
renderer.code=function({text,lang}){const hl=lang&&hljs.getLanguage(lang)?hljs.highlight(text,{language:lang}).value:hljs.highlightAuto(text).value;return `<pre><code class="hljs language-${lang||''}">${hl}</code></pre>`;};
marked.setOptions({renderer});
const STATUS_COLORS={approved:'var(--approved)',review:'var(--review)',in_progress:'var(--in_progress)',draft:'var(--draft)',outdated:'var(--outdated)'};
let currentProject=null,projectData=null,activeSection=null,activeFilter=null;

async function init(){
  const res=await fetch('/api/projects');
  const projects=await res.json();
  const sel=document.getElementById('projSelect');
  sel.innerHTML=projects.map(p=>`<option value="${p.slug}">${p.name}</option>`).join('');
  if(projects.length)switchProject(projects[0].slug);
}

async function switchProject(slug){
  currentProject=slug;
  const res=await fetch(`/api/projects/${slug}`);
  projectData=await res.json();
  document.getElementById('projName').textContent=projectData.project.name;
  document.getElementById('projMeta').textContent=`v${projectData.project.version} · ${projectData.stats.sections} sections · ${projectData.stats.words} words`;
  document.getElementById('exportBtn').href=`/api/projects/${slug}/export`;
  document.getElementById('exportBtn').download=`${slug}.md`;
  renderFilters();
  renderSections();
  renderChangelog();
  renderDepsGraph();
  activeSection=null;
  document.getElementById('mainContent').innerHTML='<div class="empty">Select a section to view</div>';
}

function renderFilters(){
  const statuses=[...new Set(projectData.sections.map(s=>s.status))];
  const tags=[...new Set(projectData.sections.flatMap(s=>s.tags||[]))];
  let html=statuses.map(s=>`<span class="chip ${activeFilter===s?'active':''}" onclick="toggleFilter('${s}')">${s.replace('_',' ')}</span>`).join('');
  html+=tags.map(t=>`<span class="chip ${activeFilter==='tag:'+t?'active':''}" onclick="toggleFilter('tag:${t}')">${t}</span>`).join('');
  document.getElementById('filters').innerHTML=html;
}

function toggleFilter(f){activeFilter=activeFilter===f?null:f;renderFilters();renderSections()}

function renderSections(){
  let secs=projectData.sections;
  if(activeFilter){
    if(activeFilter.startsWith('tag:'))secs=secs.filter(s=>(s.tags||[]).includes(activeFilter.slice(4)));
    else secs=secs.filter(s=>s.status===activeFilter);
  }
  document.getElementById('sectionList').innerHTML=secs.map(s=>`
    <div class="section-item ${activeSection===s.slug?'active':''}" onclick="loadSection('${s.slug}')">
      <div class="title"><span class="status-dot" style="background:${STATUS_COLORS[s.status]||'var(--draft)'}"></span>${s.title}</div>
      <div class="meta-line">${s.section_type} · ${s.word_count} words · ${s.revision_count||0} revs${(s.tags||[]).length?' · '+s.tags.join(', '):''}</div>
    </div>`).join('');
}

function renderChangelog(){
  const cl=projectData.changelog||[];
  document.getElementById('changelogList').innerHTML=cl.length?cl.map(c=>`
    <div class="cl-item">
      <span class="cl-section">${c.section_title}</span> rev ${c.revision_number}
      <div class="cl-desc">${c.change_description||'—'}</div>
      <div class="cl-time">${new Date(c.created_at).toLocaleString()}</div>
    </div>`).join(''):'<div class="empty">No revisions yet</div>';
}

function renderDepsGraph(){
  const deps=projectData.dependencies||[];
  if(!deps.length){document.getElementById('depsGraph').innerHTML='<div class="empty">No dependencies</div>';return}
  let html=`<div class="deps-header"><h3>Dependencies (${deps.length})</h3><p>How sections depend on each other</p></div>`;
  html+=deps.map(d=>{
    const t=d.dependency_type||'informs';
    return `<div class="dep-row">
      <span class="dep-from" onclick="loadSection('${d.from_slug}')">${d.from_title||d.from_slug}</span>
      <span class="dep-arrow">→</span>
      <span class="dep-to" onclick="loadSection('${d.to_slug}')">${d.to_title||d.to_slug}</span>
      <span class="dep-type dep-type-${t}">${t}</span>
    </div>`;
  }).join('');
  document.getElementById('depsGraph').innerHTML=html;
}

async function loadSection(slug){
  activeSection=slug;
  renderSections();
  const res=await fetch(`/api/projects/${currentProject}/sections/${slug}`);
  const data=await res.json();
  const s=data.section;
  const sc=STATUS_COLORS[s.status]||'var(--draft)';
  let html=`<div class="section-title">${s.title}</div>
    <div class="meta-row">
      <span class="badge" style="background:${sc}">${s.status.replace('_',' ')}</span>
      <span>${s.section_type}</span>
      <span>${s.word_count} words</span>
      <span>Updated ${new Date(s.updated_at).toLocaleDateString()}</span>
      ${(s.tags||[]).map(t=>`<span class="tag-chip">${t}</span>`).join('')}
    </div>`;
  if(s.summary)html+=`<div class="summary-box">${s.summary}</div>`;
  if(s.notes)html+=`<div class="notes-box"><div class="label">Notes</div>${s.notes}</div>`;
  html+=`<div class="prose">${marked.parse(s.content||'')}</div>`;
  if(data.depends_on&&data.depends_on.length){
    html+=`<div class="deps-panel"><h3>Depends On</h3>`;
    html+=data.depends_on.map(d=>`<span class="dep-chip" onclick="loadSection('${d.slug}')">${d.title}<span class="dep-type">${d.dep_type}</span></span>`).join('');
    if(data.depends_on.length)html+=`<div style="margin-top:8px;font-size:12px;color:var(--text-muted)">Context summaries loaded with this section</div>`;
    html+=`</div>`;
  }
  if(data.depended_by&&data.depended_by.length){
    html+=`<div class="deps-panel" style="margin-top:12px"><h3>Depended By</h3>`;
    html+=data.depended_by.map(d=>`<span class="dep-chip" onclick="loadSection('${d.slug}')">${d.title}<span class="dep-type">${d.dep_type}</span></span>`).join('');
    html+=`</div>`;
  }
  if(data.revisions&&data.revisions.length){
    html+=`<div class="deps-panel" style="margin-top:12px"><h3>Revision History</h3>
      <table class="rev-table"><tr><th>#</th><th>Description</th><th>Date</th></tr>`;
    html+=data.revisions.map(r=>`<tr><td>${r.revision_number}</td><td>${r.change_description||'—'}</td><td>${new Date(r.created_at).toLocaleString()}</td></tr>`).join('');
    html+=`</table></div>`;
  }
  document.getElementById('mainContent').innerHTML=html;
}

async function loadFullPRD(){
  activeSection=null;
  renderSections();
  const res=await fetch(`/api/projects/${currentProject}/export`);
  const md=await res.text();
  document.getElementById('mainContent').innerHTML=`<div class="section-title">Full PRD</div><div class="prose">${marked.parse(md)}</div>`;
}

function switchTab(tab){
  document.querySelectorAll('.tab').forEach((t,i)=>{
    const tabs=['sections','changelog','deps'];
    t.classList.toggle('active',tabs[i]===tab);
  });
  document.querySelectorAll('.tab-content').forEach(tc=>tc.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
}

init();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/projects")
async def list_projects():
    rows = await pool.fetch("""
        SELECT p.slug, p.name, p.description, p.version,
               COUNT(s.id) AS section_count,
               COALESCE(SUM(s.word_count), 0) AS total_words
        FROM projects p
        LEFT JOIN sections s ON s.project_id = p.id
        GROUP BY p.id ORDER BY p.created_at
    """)
    return [row_dict(r) for r in rows]


@app.get("/api/projects/{slug}")
async def get_project(slug: str):
    proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sections = await pool.fetch("""
        SELECT slug, title, section_type, sort_order, status, summary, tags,
               word_count, parent_slug, revision_count, updated_at
        FROM section_tree WHERE project_id = $1 ORDER BY sort_order
    """, proj["id"])

    deps = await pool.fetch("""
        SELECT s1.slug AS from_slug, s1.title AS from_title,
               s2.slug AS to_slug, s2.title AS to_title,
               d.dependency_type
        FROM section_dependencies d
        JOIN sections s1 ON s1.id = d.section_id
        JOIN sections s2 ON s2.id = d.depends_on_id
        WHERE d.project_id = $1
    """, proj["id"])

    changelog = await pool.fetch("""
        SELECT section_slug, section_title, revision_number,
               change_description, created_at
        FROM project_changelog WHERE project_slug = $1
        ORDER BY created_at DESC LIMIT 20
    """, slug)

    status_counts = {}
    total_words = 0
    for s in sections:
        st = s["status"]
        status_counts[st] = status_counts.get(st, 0) + 1
        total_words += s["word_count"]

    return {
        "project": {"slug": proj["slug"], "name": proj["name"], "description": proj["description"],
                     "version": proj["version"], "created_at": dt(proj["created_at"])},
        "stats": {"sections": len(sections), "words": total_words, "by_status": status_counts},
        "sections": [row_dict(r) for r in sections],
        "dependencies": [row_dict(r) for r in deps],
        "changelog": [row_dict(r) for r in changelog],
    }


@app.get("/api/projects/{slug}/sections/{section}")
async def get_section(slug: str, section: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sec = await pool.fetchrow("""
        SELECT s.slug, s.title, s.content, s.summary, s.status, s.section_type,
               s.tags, s.notes, s.word_count, s.updated_at
        FROM sections s WHERE s.project_id = $1 AND s.slug = $2
    """, proj["id"], section)
    if not sec:
        return JSONResponse({"error": f"section '{section}' not found"}, 404)

    sec_id = await pool.fetchval(
        "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", proj["id"], section
    )

    depends_on = await pool.fetch("""
        SELECT s.slug, s.title, s.summary, s.status,
               d.dependency_type AS dep_type, d.description AS dep_reason
        FROM section_dependencies d
        JOIN sections s ON s.id = d.depends_on_id
        WHERE d.section_id = $1
    """, sec_id)

    depended_by = await pool.fetch("""
        SELECT s.slug, s.title, s.summary, s.status,
               d.dependency_type AS dep_type, d.description AS dep_reason
        FROM section_dependencies d
        JOIN sections s ON s.id = d.section_id
        WHERE d.depends_on_id = $1
    """, sec_id)

    revisions = await pool.fetch("""
        SELECT revision_number, change_description, created_at
        FROM section_revisions WHERE section_id = $1
        ORDER BY revision_number DESC
    """, sec_id)

    return {
        "section": row_dict(sec),
        "depends_on": [row_dict(r) for r in depends_on],
        "depended_by": [row_dict(r) for r in depended_by],
        "revisions": [row_dict(r) for r in revisions],
    }


@app.get("/api/projects/{slug}/export")
async def export_project(slug: str):
    proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sections = await pool.fetch("""
        SELECT title, section_type, status, content
        FROM sections WHERE project_id = $1 ORDER BY sort_order
    """, proj["id"])

    lines = [f"# {proj['name']}\n"]
    for s in sections:
        lines.append(f"## {s['title']}")
        lines.append(f"*{s['section_type']} | {s['status']}*\n")
        lines.append(s["content"])
        lines.append("\n---\n")

    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@app.get("/health")
async def health():
    try:
        await pool.fetchval("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse({"status": "error", "db": "error"}, 503)
