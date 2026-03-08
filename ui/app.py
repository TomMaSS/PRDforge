"""PRD Forge Web UI — FastAPI application."""

import os
import sys
import uuid as _uuid
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.settings import DEFAULT_PROJECT_SETTINGS, validate_settings

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

/* Nav Rail */
.nav-rail{width:140px;min-width:140px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;justify-content:space-between;padding:12px 8px}
.nav-icons,.nav-bottom{display:flex;flex-direction:column;gap:2px}
.nav-icon{height:34px;display:flex;align-items:center;gap:8px;padding:0 10px;border-radius:8px;cursor:pointer;color:var(--text-sec);transition:all .15s;font-size:13px;white-space:nowrap}
.nav-icon:hover{background:var(--secondary);color:var(--text)}
.nav-icon.active{background:var(--accent);color:#fff}
.nav-icon svg{width:16px;height:16px;flex-shrink:0}
.nav-icon .nav-label{overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}
body.collapsed .nav-rail{width:48px;min-width:48px;padding:12px 6px;align-items:center}
body.collapsed .nav-icon{width:36px;height:36px;padding:0;justify-content:center;gap:0}
body.collapsed .nav-label{display:none}

/* Sidebar Panel */
.sidebar-panel{width:280px;min-width:280px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;transition:width .2s,min-width .2s}
body.collapsed .sidebar-panel{width:0;min-width:0;overflow:hidden}

.sidebar-header{padding:16px;border-bottom:1px solid var(--border)}
.sidebar-header h1{font-size:18px;font-weight:700;margin-bottom:4px}
.sidebar-header .meta{font-size:12px;color:var(--text-sec)}
.sidebar-header select{width:100%;margin-top:8px;padding:6px 8px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:13px}
.sidebar-header .export-btn{display:inline-block;margin-top:8px;padding:4px 12px;background:var(--accent);color:#fff;border-radius:6px;font-size:12px;text-decoration:none;font-weight:500}
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
.notes-box .label{font-weight:600;margin-bottom:4px;display:flex;align-items:center;justify-content:space-between}
.notes-box textarea{width:100%;min-height:80px;background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.25);border-radius:6px;color:#e8c060;font-family:'Inter',sans-serif;font-size:14px;line-height:1.7;padding:10px 12px;resize:vertical;margin-top:8px}
.notes-box textarea:focus{outline:none;border-color:var(--notes-accent)}
.notes-box textarea::placeholder{color:rgba(232,192,96,0.4)}
.notes-actions{display:flex;gap:8px;margin-top:8px;align-items:center}
.notes-actions button{padding:4px 14px;border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;border:none;transition:all .15s}
.notes-save{background:var(--notes-accent);color:#1a1a1a}
.notes-save:hover{opacity:0.85}
.notes-cancel{background:var(--secondary);color:var(--text-sec);border:1px solid var(--border) !important}
.notes-status{font-size:12px;color:var(--approved);opacity:0;transition:opacity .3s}
.notes-status.show{opacity:1}
.add-notes-btn{padding:6px 14px;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;border:1px solid rgba(245,158,11,0.3);background:rgba(245,158,11,0.06);color:#e8c060;margin-bottom:20px;transition:all .15s}
.add-notes-btn:hover{background:rgba(245,158,11,0.12);border-color:var(--notes-accent)}
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
.dep-row{display:flex;align-items:center;gap:4px;padding:7px 10px;border-bottom:1px solid var(--border);font-size:11px;white-space:nowrap;overflow:hidden}
.dep-row:hover{background:var(--secondary)}
.dep-from,.dep-to{font-weight:500;color:var(--text);cursor:pointer}
.dep-from:hover,.dep-to:hover{color:var(--accent)}
.dep-arrow{color:var(--accent);flex-shrink:0}
.dep-type{padding:1px 5px;border-radius:4px;font-size:9px;font-weight:500;flex-shrink:0;margin-left:auto}
.dep-type-references{background:rgba(99,102,241,0.12);color:#818cf8}
.dep-type-implements{background:rgba(59,130,246,0.12);color:#60a5fa}
.dep-type-extends{background:rgba(16,185,129,0.12);color:#34d399}
.dep-type-blocks{background:rgba(239,68,68,0.12);color:#f87171}

/* Inline comments */
.comment-hl{background:rgba(245,158,11,0.18);border-bottom:2px solid var(--notes-accent);cursor:pointer;transition:background .15s;border-radius:2px}
.comment-hl:hover,.comment-hl.active{background:rgba(245,158,11,0.35)}
.comment-hl.resolved{background:rgba(16,185,129,0.08);border-bottom-color:var(--approved);opacity:0.7}
.comment-btn{position:absolute;background:var(--notes-accent);color:#1a1a1a;border:none;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;z-index:50;box-shadow:0 4px 12px rgba(0,0,0,0.4);white-space:nowrap}
.comment-btn:hover{opacity:0.85}
.comment-popover{position:fixed;width:320px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;box-shadow:0 8px 30px rgba(0,0,0,0.4);z-index:200;font-size:13px}
.comment-popover textarea{width:100%;min-height:70px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px 10px;font-family:'Inter',sans-serif;font-size:13px;line-height:1.6;resize:vertical}
.comment-popover textarea:focus{outline:none;border-color:var(--accent)}
.comment-popover .quoted{font-size:12px;color:var(--text-muted);margin-bottom:10px;padding:6px 8px;background:var(--secondary);border-radius:4px;border-left:3px solid var(--notes-accent)}
.comments-panel{margin-top:24px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}
.comments-panel-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.comments-panel-header h3{font-size:14px;font-weight:600;color:var(--notes-accent)}
.comment-card{padding:12px 16px;border-bottom:1px solid var(--border);transition:background .1s}
.comment-card:hover{background:var(--secondary)}
.comment-card.resolved-card{opacity:0.5}
.comment-card .anchor{font-size:12px;color:var(--text-muted);margin-bottom:4px}
.comment-card .anchor em{color:var(--notes-accent)}
.comment-card .body{font-size:13px;line-height:1.6;margin-bottom:6px}
.comment-card .actions{display:flex;gap:8px;font-size:11px}
.comment-card .actions button{background:none;border:1px solid var(--border);color:var(--text-sec);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:11px}
.comment-card .actions button:hover{border-color:var(--accent);color:var(--text)}
.comment-card .actions .del-btn:hover{border-color:var(--outdated);color:var(--outdated)}

/* Comment replies */
.reply-card{margin-left:16px;padding:8px 12px;border-left:2px solid var(--border-muted);font-size:12px;color:var(--text-sec)}
.reply-card .reply-author{font-weight:600;font-size:11px;margin-bottom:2px}
.reply-card .reply-author.claude{color:var(--accent)}
.reply-card .reply-author.user{color:var(--notes-accent)}
.reply-form{margin-left:16px;margin-top:4px;display:flex;gap:6px}
.reply-form textarea{flex:1;min-height:36px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px;font-family:'Inter',sans-serif;font-size:12px;resize:vertical}
.reply-form button{padding:4px 10px;border-radius:4px;font-size:11px;font-weight:500;cursor:pointer;border:none;background:var(--accent);color:#fff}

/* Settings panel */
.settings-panel{padding:0;overflow-y:auto;flex:1}
.settings-title{padding:14px 16px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600;color:var(--text)}
.setting-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border)}
.setting-info{flex:1;min-width:0}
.setting-info label{font-size:12px;font-weight:500;color:var(--text);cursor:pointer;display:block}
.setting-info .setting-desc{font-size:10px;color:var(--text-muted);margin-top:2px}
.toggle{position:relative;width:36px;min-width:36px;height:20px;cursor:pointer;flex-shrink:0}
.toggle input{opacity:0;width:0;height:0}
.toggle .slider{position:absolute;inset:0;background:var(--secondary);border-radius:10px;transition:.2s;border:1px solid var(--border)}
.toggle .slider:before{content:'';position:absolute;height:14px;width:14px;left:2px;bottom:2px;background:var(--text-sec);border-radius:50%;transition:.2s}
.toggle input:checked+.slider{background:var(--accent);border-color:var(--accent)}
.toggle input:checked+.slider:before{transform:translateX(16px);background:#fff}
.settings-note{padding:12px 16px;font-size:11px;color:var(--text-muted);line-height:1.5}

/* Empty state */
.empty{display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:16px}

/* Tab content */
.tab-content{display:none;flex:1;overflow-y:auto}
.tab-content.active{display:flex;flex-direction:column}
</style>
</head>
<body>
<div class="nav-rail" id="navRail">
  <div class="nav-icons">
    <div class="nav-icon active" data-tab="sections" onclick="switchTab('sections')" title="Sections">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 13H8"/><path d="M16 17H8"/><path d="M16 13h-2"/></svg>
      <span class="nav-label">Sections</span>
    </div>
    <div class="nav-icon" data-tab="comments" onclick="switchTab('comments')" title="Comments">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span class="nav-label">Comments</span>
    </div>
    <div class="nav-icon" data-tab="deps" onclick="switchTab('deps')" title="Deps">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" x2="6" y1="3" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>
      <span class="nav-label">Dependencies</span>
    </div>
    <div class="nav-icon" data-tab="changelog" onclick="switchTab('changelog')" title="Changelog">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
      <span class="nav-label">Changelog</span>
    </div>
  </div>
  <div class="nav-bottom">
    <div class="nav-icon" data-tab="settings" onclick="switchTab('settings')" title="Settings">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      <span class="nav-label">Settings</span>
    </div>
    <div class="nav-icon" onclick="toggleSidebar()" id="collapseBtn" title="Collapse">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
      <span class="nav-label">Collapse</span>
    </div>
  </div>
</div>
<div class="sidebar-panel" id="sidebarPanel">
  <div class="sidebar-header">
    <h1 id="projName">PRD Forge</h1>
    <div class="meta" id="projMeta"></div>
    <select id="projSelect" onchange="switchProject(this.value)"></select>
    <div style="display:flex;gap:8px;margin-top:8px">
      <a class="export-btn" id="exportBtn" href="#" download>Export</a>
      <a class="export-btn" href="#" onclick="loadFullPRD();return false" style="background:var(--secondary);border:1px solid var(--border)">View Full PRD</a>
    </div>
  </div>
  <div class="tab-content active" id="tab-sections">
    <div class="filters" id="filters"></div>
    <div class="section-list" id="sectionList"></div>
  </div>
  <div class="tab-content" id="tab-comments">
    <div class="filters" id="commentFilters"></div>
    <div class="section-list" id="globalCommentsList"></div>
  </div>
  <div class="tab-content" id="tab-deps">
    <div class="deps-graph" id="depsGraph"></div>
  </div>
  <div class="tab-content" id="tab-changelog">
    <div class="changelog-list" id="changelogList"></div>
  </div>
  <div class="tab-content" id="tab-settings">
    <div class="settings-panel" id="settingsPanel">
      <div class="settings-title">Project Settings</div>
      <div class="setting-row">
        <div class="setting-info">
          <label for="settingClaudeReplies">Claude comment replies</label>
          <div class="setting-desc">Auto-reply to comments before resolving</div>
        </div>
        <label class="toggle">
          <input type="checkbox" id="settingClaudeReplies" onchange="saveSetting('claude_comment_replies',this.checked)">
          <span class="slider"></span>
        </label>
      </div>
      <div class="settings-note">Settings are per-project and synced with MCP tools. Changes take effect immediately.</div>
    </div>
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
  loadGlobalComments();
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
      <span class="dep-from" onclick="loadSection('${d.from_slug}')">${d.from_slug}</span>
      <span class="dep-arrow">→</span>
      <span class="dep-to" onclick="loadSection('${d.to_slug}')">${d.to_slug}</span>
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
  html+=renderNotesBox(s.notes||'',s.slug);
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
  if(data.comments&&data.comments.length){
    applyCommentHighlights(data.comments);
    renderCommentsPanel(data.comments);
  }
}

function renderNotesBox(notes,slug){
  if(notes){
    return `<div class="notes-box" id="notesBox">
      <div class="label"><span>Notes</span><button class="notes-cancel" onclick="toggleNotesEdit(true)" style="font-size:11px;padding:2px 8px">Edit</button></div>
      <div id="notesDisplay">${marked.parse(notes)}</div>
      <div id="notesEdit" style="display:none">
        <textarea id="notesTextarea">${notes.replace(/</g,'&lt;')}</textarea>
        <div class="notes-actions">
          <button class="notes-save" onclick="saveNotes('${slug}')">Save</button>
          <button class="notes-cancel" onclick="toggleNotesEdit(false)">Cancel</button>
          <span class="notes-status" id="notesStatus">Saved</span>
        </div>
      </div>
    </div>`;
  }
  return `<button class="add-notes-btn" onclick="addNotesBox('${slug}')">+ Add Notes</button>
    <div class="notes-box" id="notesBox" style="display:none">
      <div class="label"><span>Notes</span></div>
      <textarea id="notesTextarea" placeholder="Add change requests, feedback, or requirements for Claude to implement..."></textarea>
      <div class="notes-actions">
        <button class="notes-save" onclick="saveNotes('${slug}')">Save</button>
        <button class="notes-cancel" onclick="document.getElementById('notesBox').style.display='none';document.querySelector('.add-notes-btn').style.display=''">Cancel</button>
        <span class="notes-status" id="notesStatus">Saved</span>
      </div>
    </div>`;
}
function addNotesBox(slug){document.querySelector('.add-notes-btn').style.display='none';document.getElementById('notesBox').style.display=''}
function toggleNotesEdit(show){document.getElementById('notesDisplay').style.display=show?'none':'';document.getElementById('notesEdit').style.display=show?'':'none'}
async function saveNotes(slug){
  const notes=document.getElementById('notesTextarea').value;
  const res=await fetch(`/api/projects/${currentProject}/sections/${slug}/notes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({notes})});
  if(res.ok){
    const st=document.getElementById('notesStatus');st.classList.add('show');setTimeout(()=>st.classList.remove('show'),2000);
    loadSection(slug);
  }
}

/* --- Inline comments --- */
let _commentSelection=null;
document.addEventListener('mouseup',function(e){
  if(e.target.closest('.comment-btn')||e.target.closest('.comment-popover'))return;
  document.querySelectorAll('.comment-btn').forEach(b=>b.remove());
  const sel=window.getSelection();
  if(!sel||sel.isCollapsed||!activeSection)return;
  const prose=document.querySelector('.prose');
  if(!prose||!prose.contains(sel.anchorNode))return;
  const text=sel.toString().trim();
  if(!text||text.length<3)return;
  const range=sel.getRangeAt(0);
  _commentSelection={text,range:range.cloneRange()};
  const rect=range.getBoundingClientRect();
  const mainEl=document.querySelector('.main');
  if(!mainEl)return;
  const btn=document.createElement('button');
  btn.className='comment-btn';
  btn.textContent='+ Comment';
  btn.style.position='fixed';
  btn.style.top=(rect.top-36)+'px';
  btn.style.left=rect.left+'px';
  btn.style.zIndex='1000';
  document.body.appendChild(btn);
  btn.addEventListener('click',function(ev){
    ev.preventDefault();ev.stopPropagation();
    showCommentInput(_commentSelection.text,_commentSelection.range);
  });
});
document.addEventListener('mousedown',function(e){
  if(e.target.closest('.comment-btn')||e.target.closest('.comment-popover'))return;
  document.querySelectorAll('.comment-btn').forEach(b=>b.remove());
  document.querySelectorAll('.comment-popover').forEach(p=>p.remove());
});

function getAnchorContext(range){
  const prose=document.querySelector('.prose');
  if(!prose)return{anchor_text:range.toString().trim(),anchor_prefix:'',anchor_suffix:''};
  const full=prose.textContent;
  const text=range.toString().trim();
  const walker=document.createTreeWalker(prose,NodeFilter.SHOW_TEXT);
  let offset=0,found=false;
  while(walker.nextNode()){
    if(walker.currentNode===range.startContainer){offset+=range.startOffset;found=true;break}
    offset+=walker.currentNode.textContent.length;
  }
  const prefix=found?full.substring(Math.max(0,offset-40),offset):'';
  const suffix=found?full.substring(offset+text.length,offset+text.length+40):'';
  return{anchor_text:text,anchor_prefix:prefix,anchor_suffix:suffix};
}

function showCommentInput(text,range){
  document.querySelectorAll('.comment-btn,.comment-popover').forEach(b=>b.remove());
  const anchor=getAnchorContext(range);
  const rect=range.getBoundingClientRect();
  const pop=document.createElement('div');
  pop.className='comment-popover';
  pop.style.top=(rect.bottom+8)+'px';
  pop.style.left=Math.min(rect.left,window.innerWidth-340)+'px';
  const short=text.length>80?text.substring(0,80)+'...':text;
  pop.innerHTML=`<div class="quoted">"${short.replace(/</g,'&lt;')}"</div>
    <textarea placeholder="Your comment..."></textarea>
    <div style="display:flex;gap:8px;margin-top:8px">
      <button class="notes-save" onclick="submitComment(this)">Save</button>
      <button class="notes-cancel" onclick="this.closest('.comment-popover').remove()">Cancel</button>
    </div>`;
  pop.dataset.anchor=JSON.stringify(anchor);
  document.body.appendChild(pop);
  pop.querySelector('textarea').focus();
}

async function submitComment(btn){
  const pop=btn.closest('.comment-popover');
  const anchor=JSON.parse(pop.dataset.anchor);
  const body=pop.querySelector('textarea').value.trim();
  if(!body)return;
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments`,{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({...anchor,body})
  });
  pop.remove();
  window.getSelection().removeAllRanges();
  loadSection(activeSection);
}

function applyCommentHighlights(comments){
  const prose=document.querySelector('.prose');
  if(!prose)return;
  const open=comments.filter(c=>!c.resolved);
  open.forEach(c=>{
    highlightInDOM(prose,c.anchor_text,c.anchor_prefix,c.anchor_suffix,c.id);
  });
}

function highlightInDOM(root,text,prefix,suffix,cid){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  let nodes=[],full='';
  while(walker.nextNode()){nodes.push({node:walker.currentNode,start:full.length});full+=walker.currentNode.textContent}
  let searchCtx=prefix+text+suffix;
  let idx=full.indexOf(searchCtx);
  let startIdx,endIdx;
  if(idx!==-1){startIdx=idx+prefix.length;endIdx=startIdx+text.length}
  else{idx=full.indexOf(text);if(idx===-1)return;startIdx=idx;endIdx=idx+text.length}
  // Find start and end text nodes
  let sn=null,so=0,en=null,eo=0;
  for(const n of nodes){
    const nEnd=n.start+n.node.textContent.length;
    if(!sn&&startIdx<nEnd){sn=n.node;so=startIdx-n.start}
    if(endIdx<=nEnd){en=n.node;eo=endIdx-n.start;break}
  }
  if(!sn||!en)return;
  try{
    const range=document.createRange();
    range.setStart(sn,so);
    range.setEnd(en,eo);
    const mark=document.createElement('mark');
    mark.className='comment-hl';
    mark.dataset.commentId=cid;
    mark.onclick=function(){scrollToComment(cid)};
    range.surroundContents(mark);
  }catch(e){/* cross-element selection — skip highlight, comment still in panel */}
}

function scrollToComment(cid){
  const card=document.querySelector(`.comment-card[data-id="${cid}"]`);
  if(card){card.scrollIntoView({behavior:'smooth',block:'center'});card.style.background='var(--secondary)';setTimeout(()=>card.style.background='',1500)}
}

async function resolveComment(cid){
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments/${cid}/resolve`,{method:'POST'});
  loadSection(activeSection);
}
async function deleteComment(cid){
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments/${cid}`,{method:'DELETE'});
  loadSection(activeSection);
}

function renderCommentsPanel(comments){
  if(!comments.length)return;
  const wrap=document.querySelector('.content-wrap');
  const open=comments.filter(c=>!c.resolved);
  const resolved=comments.filter(c=>c.resolved);
  let html=`<div class="comments-panel"><div class="comments-panel-header"><h3>Comments (${open.length} open${resolved.length?', '+resolved.length+' resolved':''})</h3></div>`;
  comments.forEach(c=>{
    const short=c.anchor_text.length>60?c.anchor_text.substring(0,60)+'...':c.anchor_text;
    html+=`<div class="comment-card ${c.resolved?'resolved-card':''}" data-id="${c.id}">
      <div class="anchor">on "<em>${short.replace(/</g,'&lt;')}</em>" · ${new Date(c.created_at).toLocaleString()}</div>
      <div class="body">${marked.parse(c.body)}</div>`;
    // Render replies
    if(c.replies&&c.replies.length){
      c.replies.forEach(r=>{
        html+=`<div class="reply-card">
          <div class="reply-author ${r.author}">${r.author} · ${new Date(r.created_at).toLocaleString()}</div>
          <div>${marked.parse(r.body)}</div>
        </div>`;
      });
    }
    html+=`<div class="actions">
        <button onclick="resolveComment('${c.id}')">${c.resolved?'Reopen':'Resolve'}</button>
        <button onclick="showReplyForm('${c.id}')">Reply</button>
        <button class="del-btn" onclick="deleteComment('${c.id}')">Delete</button>
      </div>
      <div class="reply-form" id="reply-form-${c.id}" style="display:none">
        <textarea placeholder="Write a reply..."></textarea>
        <button onclick="submitReply('${c.id}',this)">Send</button>
      </div>
    </div>`;
  });
  html+='</div>';
  wrap.insertAdjacentHTML('beforeend',html);
}

function showReplyForm(cid){
  const f=document.getElementById('reply-form-'+cid);
  f.style.display=f.style.display==='none'?'flex':'none';
  if(f.style.display==='flex')f.querySelector('textarea').focus();
}

async function submitReply(cid,btn){
  const form=btn.closest('.reply-form');
  const body=form.querySelector('textarea').value.trim();
  if(!body)return;
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments/${cid}/replies`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({body})
  });
  loadSection(activeSection);
}

/* --- Global comments tab --- */
let _globalComments=[],_commentFilter='all';
async function loadGlobalComments(){
  const res=await fetch(`/api/projects/${currentProject}/comments`);
  _globalComments=await res.json();
  renderGlobalCommentFilters();
  renderGlobalComments();
}
function renderGlobalCommentFilters(){
  const total=_globalComments.length;
  const openCount=_globalComments.filter(c=>!c.resolved).length;
  const resolvedCount=total-openCount;
  const f=document.getElementById('commentFilters');
  f.innerHTML=[
    {key:'all',label:`All (${total})`},{key:'open',label:`Open (${openCount})`},{key:'resolved',label:`Resolved (${resolvedCount})`}
  ].map(c=>`<span class="chip ${_commentFilter===c.key?'active':''}" onclick="setCommentFilter('${c.key}')">${c.label}</span>`).join('');
}
function setCommentFilter(f){_commentFilter=f;renderGlobalCommentFilters();renderGlobalComments()}
function renderGlobalComments(){
  let list=_globalComments;
  if(_commentFilter==='open')list=list.filter(c=>!c.resolved);
  else if(_commentFilter==='resolved')list=list.filter(c=>c.resolved);
  const el=document.getElementById('globalCommentsList');
  if(!list.length){el.innerHTML='<div class="empty" style="padding:40px">No comments</div>';return}
  el.innerHTML=list.map(c=>{
    const short=c.anchor_text.length>50?c.anchor_text.substring(0,50)+'...':c.anchor_text;
    const time=new Date(c.created_at).toLocaleString();
    const status=c.resolved?'<span style="color:var(--approved)">Resolved ✓</span>':'<span style="color:var(--text-sec)">Open</span>';
    return `<div class="section-item ${c.resolved?'':'active'}" style="${c.resolved?'opacity:0.55':''};border-left:3px solid ${c.resolved?'var(--approved)':'var(--accent)'}" onclick="goToComment('${c.section_slug}','${c.id}')">
      <div class="title" style="font-size:12px;font-weight:600;color:var(--accent)">${c.section_title||c.section_slug}</div>
      <div style="font-size:12px;font-style:italic;color:var(--text);margin:2px 0">"${short.replace(/</g,'&lt;')}"</div>
      <div style="font-size:12px;color:var(--text-sec);margin:2px 0">${c.body.length>80?c.body.substring(0,80).replace(/</g,'&lt;')+'...':c.body.replace(/</g,'&lt;')}</div>
      <div class="meta-line">${time} · ${status}</div>
    </div>`;
  }).join('');
}
function goToComment(sectionSlug,commentId){
  switchTab('sections');
  loadSection(sectionSlug).then(()=>{
    setTimeout(()=>{
      const hl=document.querySelector(`.comment-hl[data-comment-id="${commentId}"]`);
      if(hl){hl.scrollIntoView({behavior:'smooth',block:'center'});hl.classList.add('active');setTimeout(()=>hl.classList.remove('active'),2000)}
      scrollToComment(commentId);
    },200);
  });
}

async function loadFullPRD(){
  activeSection=null;
  renderSections();
  const res=await fetch(`/api/projects/${currentProject}/export`);
  const md=await res.text();
  document.getElementById('mainContent').innerHTML=`<div class="section-title">Full PRD</div><div class="prose">${marked.parse(md)}</div>`;
}

function switchTab(tab){
  document.querySelectorAll('.nav-icon[data-tab]').forEach(n=>n.classList.toggle('active',n.dataset.tab===tab));
  document.querySelectorAll('.tab-content').forEach(tc=>tc.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  if(document.body.classList.contains('collapsed'))document.body.classList.remove('collapsed');
  if(tab==='comments')loadGlobalComments();
  if(tab==='settings')loadSettings();
}

function toggleSidebar(){
  document.body.classList.toggle('collapsed');
  const btn=document.getElementById('collapseBtn');
  const collapsed=document.body.classList.contains('collapsed');
  btn.innerHTML=collapsed
    ?'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>'
    :'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>';
}

async function loadSettings(){
  if(!currentProject)return;
  const res=await fetch(`/api/projects/${currentProject}/settings`);
  const data=await res.json();
  document.getElementById('settingClaudeReplies').checked=data.claude_comment_replies!==false;
}

async function saveSetting(key,value){
  if(!currentProject)return;
  await fetch(`/api/projects/${currentProject}/settings`,{
    method:'PUT',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({[key]:value})
  });
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

    comments = await pool.fetch("""
        SELECT id, anchor_text, anchor_prefix, anchor_suffix, body, resolved, created_at
        FROM section_comments WHERE section_id = $1
        ORDER BY created_at
    """, sec_id)

    # Batch-fetch replies
    comment_ids = [c["id"] for c in comments]
    replies = await pool.fetch(
        "SELECT id, comment_id, author, body, created_at "
        "FROM comment_replies WHERE comment_id = ANY($1) ORDER BY created_at",
        comment_ids,
    ) if comment_ids else []

    replies_by_comment = {}
    for r in replies:
        cid = str(r["comment_id"])
        replies_by_comment.setdefault(cid, []).append(row_dict(r))

    comment_dicts = []
    for c in comments:
        cd = row_dict(c)
        cd["replies"] = replies_by_comment.get(str(c["id"]), [])
        comment_dicts.append(cd)

    return {
        "section": row_dict(sec),
        "depends_on": [row_dict(r) for r in depends_on],
        "depended_by": [row_dict(r) for r in depended_by],
        "revisions": [row_dict(r) for r in revisions],
        "comments": comment_dicts,
    }


@app.post("/api/projects/{slug}/sections/{section}/notes")
async def update_notes(slug: str, section: str, request: Request):
    body = await request.json()
    notes = body.get("notes", "")
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    result = await pool.execute(
        "UPDATE sections SET notes = $1 WHERE project_id = $2 AND slug = $3",
        notes, proj["id"], section,
    )
    if result.split()[-1] == "0":
        return JSONResponse({"error": f"section '{section}' not found"}, 404)
    return {"ok": True, "notes": notes}


@app.post("/api/projects/{slug}/sections/{section}/comments")
async def create_comment(slug: str, section: str, request: Request):
    body = await request.json()
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    sec_id = await pool.fetchval(
        "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", proj["id"], section
    )
    if not sec_id:
        return JSONResponse({"error": f"section '{section}' not found"}, 404)
    row = await pool.fetchrow("""
        INSERT INTO section_comments (section_id, anchor_text, anchor_prefix, anchor_suffix, body)
        VALUES ($1, $2, $3, $4, $5) RETURNING *
    """, sec_id, body["anchor_text"], body.get("anchor_prefix", ""),
        body.get("anchor_suffix", ""), body["body"])
    return row_dict(row)


@app.post("/api/projects/{slug}/sections/{section}/comments/{comment_id}/resolve")
async def resolve_comment(slug: str, section: str, comment_id: str):
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id, c.resolved FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("UPDATE section_comments SET resolved = $1 WHERE id = $2", not row["resolved"], row["id"])
    return {"ok": True, "resolved": not row["resolved"]}


@app.delete("/api/projects/{slug}/sections/{section}/comments/{comment_id}")
async def delete_comment(slug: str, section: str, comment_id: str):
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("DELETE FROM section_comments WHERE id = $1", row["id"])
    return {"ok": True}


@app.post("/api/projects/{slug}/sections/{section}/comments/{comment_id}/replies")
async def add_comment_reply(slug: str, section: str, comment_id: str, request: Request):
    body = await request.json()
    reply_body = body.get("body", "").strip()
    if not reply_body:
        return JSONResponse({"error": "body required"}, 400)
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    reply = await pool.fetchrow(
        "INSERT INTO comment_replies (comment_id, author, body) VALUES ($1, 'user', $2) RETURNING *",
        row["id"], reply_body,
    )
    return row_dict(reply)


@app.get("/api/projects/{slug}/settings")
async def get_settings(slug: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", proj["id"]
    )
    if row:
        import json as _json2
        raw = row["settings"]
        db_settings = _json2.loads(raw) if isinstance(raw, str) else dict(raw)
    else:
        db_settings = {}
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    return merged


@app.put("/api/projects/{slug}/settings")
async def update_settings(slug: str, request: Request):
    body = await request.json()
    clean, errors = validate_settings(body)
    if errors:
        return JSONResponse({"error": f"invalid settings: {'; '.join(errors)}"}, 400)
    if not clean:
        return JSONResponse({"error": "no valid settings provided"}, 400)
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    import json as _json
    await pool.execute("""
        INSERT INTO project_settings (project_id, settings)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (project_id)
        DO UPDATE SET settings = project_settings.settings || $2::jsonb
    """, proj["id"], _json.dumps(clean))
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", proj["id"]
    )
    raw = row["settings"]
    db_settings = _json.loads(raw) if isinstance(raw, str) else dict(raw)
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    return merged


@app.get("/api/projects/{slug}/comments")
async def list_project_comments(slug: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    rows = await pool.fetch("""
        SELECT c.id, c.anchor_text, c.anchor_prefix, c.anchor_suffix,
               c.body, c.resolved, c.created_at, c.updated_at,
               s.slug AS section_slug, s.title AS section_title,
               COALESCE(rc.cnt, 0) AS reply_count
        FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        LEFT JOIN (SELECT comment_id, COUNT(*) AS cnt FROM comment_replies GROUP BY comment_id) rc
            ON rc.comment_id = c.id
        WHERE s.project_id = $1
        ORDER BY c.created_at DESC
    """, proj["id"])
    return [row_dict(r) for r in rows]


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
